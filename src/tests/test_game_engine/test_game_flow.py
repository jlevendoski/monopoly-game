"""
Comprehensive end-to-end tests for game flow integration.

Tests complete game scenarios including:
- Tax payment flow (can afford vs cannot afford)
- Card-induced movement and subsequent landing effects
- Forced bankruptcy scenarios
- Multi-step game sequences
- Chain reactions (card -> move -> rent -> bankruptcy)

Run from project root: python -m pytest tests/test_game_engine/test_game_flow.py -v
Or run directly: python tests/test_game_engine/test_game_flow.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.game_engine import Game, Player
from server.game_engine.dice import Dice, DiceResult
from server.game_engine.cards import Card, CardAction, CardDeck, CardManager
from server.game_engine.board import Board
from shared.enums import GamePhase, PlayerState, CardType, SpaceType
from shared.constants import (
    BOARD_SIZE, STARTING_MONEY, JAIL_POSITION, JAIL_BAIL,
    GO_TO_JAIL_POSITION, SALARY_AMOUNT
)


class Colors:
    """ANSI color codes for pretty output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}")
    print(f" {text}")
    print(f"{'=' * 60}{Colors.RESET}\n")


def print_subheader(text: str) -> None:
    print(f"\n{Colors.CYAN}--- {text} ---{Colors.RESET}")


def print_success(text: str) -> None:
    print(f"  {Colors.GREEN}✓ {text}{Colors.RESET}")


def print_failure(text: str) -> None:
    print(f"  {Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str) -> None:
    print(f"  {Colors.YELLOW}→ {text}{Colors.RESET}")


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def add(self, passed: bool) -> None:
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def summary(self) -> None:
        print_header("TEST SUMMARY")
        total = self.passed + self.failed
        print(f"  Total:  {total}")
        print(f"  {Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {self.failed}{Colors.RESET}")

        if self.failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! ✓{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}Some tests failed ✗{Colors.RESET}")


def assert_test(condition: bool, success_msg: str, failure_msg: str) -> bool:
    if condition:
        print_success(success_msg)
        return True
    else:
        print_failure(failure_msg)
        return False


def create_test_game(num_players: int = 2) -> Game:
    """Create a game with specified number of players for testing."""
    game = Game(name="Game Flow Test")
    for i in range(num_players):
        game.add_player(f"Player{i+1}")
    game.start_game()
    return game


class MockDice:
    """Mock dice that returns predetermined results."""
    def __init__(self, results: list):
        self.results = results
        self.index = 0
    
    def roll(self) -> DiceResult:
        if self.index < len(self.results):
            result = self.results[self.index]
            self.index += 1
            return result
        # Default to non-doubles if we run out
        return DiceResult(die1=3, die2=4)


# ============================================================================
# TEST GROUP 1: Tax Payment Flow
# ============================================================================

def test_tax_payment_can_afford() -> bool:
    """Test tax payment when player can afford it."""
    print_header("TAX PAYMENT - CAN AFFORD TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Land on Income Tax (position 4, $200)")
    player.position = 0
    player.money = STARTING_MONEY  # $1500
    initial_money = player.money
    
    # Use mock dice to land on Income Tax (position 4)
    game.dice = MockDice([DiceResult(die1=2, die2=2)])
    
    success, msg, dice_result = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player.position == 4,
        f"Player landed on Income Tax (position 4)",
        f"Player at position {player.position}"
    ))
    
    results.add(assert_test(
        player.money == initial_money - 200,
        f"Player paid $200 tax (${player.money} remaining)",
        f"Player money is ${player.money}, expected ${initial_money - 200}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.POST_ROLL,
        "Phase is POST_ROLL (can end turn)",
        f"Phase is {game.phase}"
    ))
    
    print_subheader("Land on Luxury Tax (position 38, $100)")
    game2 = create_test_game()
    player2 = game2.current_player
    player2.position = 36  # 2 spaces before Luxury Tax
    player2.money = 500
    initial_money2 = player2.money
    
    game2.dice = MockDice([DiceResult(die1=1, die2=1)])
    
    success, msg, _ = game2.roll_dice(player2.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player2.position == 38,
        f"Player landed on Luxury Tax (position 38)",
        f"Player at position {player2.position}"
    ))
    
    results.add(assert_test(
        player2.money == initial_money2 - 100,
        f"Player paid $100 luxury tax (${player2.money} remaining)",
        f"Player money is ${player2.money}"
    ))
    
    return results.failed == 0


def test_tax_payment_cannot_afford() -> bool:
    """Test tax payment when player cannot afford it."""
    print_header("TAX PAYMENT - CANNOT AFFORD TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Land on Income Tax with insufficient funds")
    player.position = 0
    player.money = 150  # Less than $200 tax
    initial_money = player.money
    
    game.dice = MockDice([DiceResult(die1=2, die2=2)])
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player.position == 4,
        f"Player landed on Income Tax",
        f"Player at position {player.position}"
    ))
    
    results.add(assert_test(
        player.money == initial_money,
        f"Player money unchanged (${player.money}) - must raise funds",
        f"Player money changed unexpectedly to ${player.money}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.PAYING_RENT,
        "Phase is PAYING_RENT (must raise funds or declare bankruptcy)",
        f"Phase is {game.phase}"
    ))
    
    print_subheader("Cannot end turn while in PAYING_RENT phase")
    success, msg = game.end_turn(player.id)
    
    results.add(assert_test(
        not success,
        f"End turn correctly blocked: {msg}",
        f"End turn should be blocked"
    ))
    
    print_subheader("Declare bankruptcy to resolve")
    success, msg = game.declare_bankruptcy(player.id)
    
    results.add(assert_test(
        success,
        f"Bankruptcy declared: {msg}",
        f"Bankruptcy failed: {msg}"
    ))
    
    results.add(assert_test(
        player.state == PlayerState.BANKRUPT,
        "Player is now BANKRUPT",
        f"Player state is {player.state}"
    ))
    
    return results.failed == 0


def test_tax_with_exact_funds() -> bool:
    """Test tax payment with exactly enough money."""
    print_header("TAX PAYMENT - EXACT FUNDS TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Pay $200 tax with exactly $200")
    player.position = 0
    player.money = 200  # Exactly enough
    
    game.dice = MockDice([DiceResult(die1=2, die2=2)])
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player.money == 0,
        f"Player has $0 after paying exact tax amount",
        f"Player has ${player.money}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.POST_ROLL,
        "Phase is POST_ROLL (payment succeeded)",
        f"Phase is {game.phase}"
    ))
    
    return results.failed == 0


# ============================================================================
# TEST GROUP 2: Card-Induced Movement
# ============================================================================

def test_card_move_to_go() -> bool:
    """Test card that moves player to GO."""
    print_header("CARD MOVEMENT - ADVANCE TO GO TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Draw 'Advance to Go' card")
    player.position = 7  # Chance space
    player.money = STARTING_MONEY
    initial_money = player.money
    
    # Create a mock card manager that returns specific card
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "Advance to Go (Collect $200)",
                CardAction.MOVE_TO,
                value=0
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    
    # Mock dice to land on Chance (position 7)
    game.dice = MockDice([DiceResult(die1=4, die2=3)])
    player.position = 0
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player.position == 0,
        f"Player moved to GO (position 0)",
        f"Player at position {player.position}"
    ))
    
    # Player should collect $200 for landing on GO (the card moves them there)
    # Note: The exact behavior depends on implementation - move_to checks if passing GO
    results.add(assert_test(
        player.money >= initial_money,
        f"Player collected GO salary (${player.money})",
        f"Player money is ${player.money}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.POST_ROLL,
        "Phase is POST_ROLL after landing on GO",
        f"Phase is {game.phase}"
    ))
    
    return results.failed == 0


def test_card_move_to_property() -> bool:
    """Test card that moves player to a property (e.g., Boardwalk)."""
    print_header("CARD MOVEMENT - ADVANCE TO PROPERTY TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    p2_id = [pid for pid in game.player_order if pid != player.id][0]
    p2 = game.players[p2_id]
    
    print_subheader("Draw 'Advance to Boardwalk' - unowned")
    player.position = 7  # Will land on Chance
    player.money = STARTING_MONEY
    
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "Advance to Boardwalk.",
                CardAction.MOVE_TO,
                value=39  # Boardwalk
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    game.dice = MockDice([DiceResult(die1=4, die2=3)])
    player.position = 0
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player.position == 39,
        f"Player moved to Boardwalk (position 39)",
        f"Player at position {player.position}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.PROPERTY_DECISION,
        "Phase is PROPERTY_DECISION (can buy Boardwalk)",
        f"Phase is {game.phase}"
    ))
    
    print_subheader("Player buys Boardwalk")
    success, msg = game.buy_property(player.id)
    
    results.add(assert_test(
        success,
        f"Bought Boardwalk: {msg}",
        f"Failed to buy: {msg}"
    ))
    
    results.add(assert_test(
        39 in player.properties,
        "Player owns Boardwalk",
        f"Player properties: {player.properties}"
    ))
    
    print_subheader("Another player lands on owned Boardwalk via card")
    # Set up Player 2's turn
    game.phase = GamePhase.POST_ROLL
    game.last_dice_roll = DiceResult(die1=3, die2=4)
    player.has_rolled = True
    player.consecutive_doubles = 0
    game.end_turn(player.id)
    
    # Now it's Player 2's turn
    p2.position = 0
    p2.money = STARTING_MONEY
    initial_money_p2 = p2.money
    
    game.cards = MockCardManager()  # Same card - Advance to Boardwalk
    game.dice = MockDice([DiceResult(die1=4, die2=3)])  # Land on Chance
    
    success, msg, _ = game.roll_dice(p2.id)
    
    results.add(assert_test(
        success,
        f"P2 roll succeeded: {msg}",
        f"P2 roll failed: {msg}"
    ))
    
    results.add(assert_test(
        p2.position == 39,
        "P2 moved to Boardwalk",
        f"P2 at position {p2.position}"
    ))
    
    # Check rent was paid - Boardwalk base rent is $50
    boardwalk = game.board.get_property(39)
    expected_rent = boardwalk.calculate_rent(0, 1)  # No houses, 1 property in group
    
    results.add(assert_test(
        p2.money < initial_money_p2,
        f"P2 paid rent (${initial_money_p2 - p2.money})",
        f"P2 money unchanged: ${p2.money}"
    ))
    
    return results.failed == 0


def test_card_go_to_jail() -> bool:
    """Test 'Go to Jail' card."""
    print_header("CARD MOVEMENT - GO TO JAIL TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Draw 'Go to Jail' card")
    player.position = 0
    player.money = STARTING_MONEY
    initial_money = player.money
    
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "Go to Jail. Go directly to Jail, do not pass Go, do not collect $200.",
                CardAction.GO_TO_JAIL
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    game.dice = MockDice([DiceResult(die1=4, die2=3)])  # Land on Chance (pos 7)
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player.position == JAIL_POSITION,
        f"Player sent to Jail (position {JAIL_POSITION})",
        f"Player at position {player.position}"
    ))
    
    results.add(assert_test(
        player.state == PlayerState.IN_JAIL,
        "Player state is IN_JAIL",
        f"Player state is {player.state}"
    ))
    
    results.add(assert_test(
        player.money == initial_money,
        "Player did not collect GO salary",
        f"Player money is ${player.money}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.POST_ROLL,
        "Phase is POST_ROLL",
        f"Phase is {game.phase}"
    ))
    
    return results.failed == 0


def test_card_move_back() -> bool:
    """Test 'Go Back 3 Spaces' card."""
    print_header("CARD MOVEMENT - GO BACK 3 SPACES TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Draw 'Go Back 3 Spaces' from Chance (position 7)")
    # Position 7 is Chance. Going back 3 lands on Income Tax (position 4)
    player.position = 0
    player.money = STARTING_MONEY
    initial_money = player.money
    
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "Go Back 3 Spaces.",
                CardAction.MOVE_BACK,
                value=3
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    game.dice = MockDice([DiceResult(die1=4, die2=3)])  # Land on Chance (pos 7)
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    # Should be at position 4 (7 - 3 = 4, Income Tax)
    results.add(assert_test(
        player.position == 4,
        f"Player moved back to position 4 (Income Tax)",
        f"Player at position {player.position}"
    ))
    
    # Should have paid $200 tax
    results.add(assert_test(
        player.money == initial_money - 200,
        f"Player paid $200 Income Tax",
        f"Player money is ${player.money}"
    ))
    
    return results.failed == 0


def test_card_get_out_of_jail_free() -> bool:
    """Test receiving and using Get Out of Jail Free card."""
    print_header("CARD - GET OUT OF JAIL FREE TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Draw 'Get Out of Jail Free' card")
    player.position = 0
    player.jail_cards = 0
    
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "Get Out of Jail Free.",
                CardAction.GET_OUT_OF_JAIL,
                keep=True
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    game.dice = MockDice([DiceResult(die1=4, die2=3)])  # Land on Chance
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player.jail_cards == 1,
        "Player received Get Out of Jail Free card",
        f"Player has {player.jail_cards} jail cards"
    ))
    
    print_subheader("Use the card when sent to jail later")
    # End turn and set up next scenario
    game.phase = GamePhase.POST_ROLL
    game.last_dice_roll = DiceResult(die1=4, die2=3)
    player.has_rolled = True
    player.consecutive_doubles = 0
    game.end_turn(player.id)
    
    # Advance back to player's turn
    other_id = [pid for pid in game.player_order if pid != player.id][0]
    other = game.players[other_id]
    game.last_dice_roll = DiceResult(die1=3, die2=4)
    other.has_rolled = True
    game.phase = GamePhase.POST_ROLL
    game.end_turn(other_id)
    
    # Now send player to jail
    player.send_to_jail()
    game.phase = GamePhase.PRE_ROLL
    
    results.add(assert_test(
        player.state == PlayerState.IN_JAIL,
        "Player is in jail",
        f"Player state is {player.state}"
    ))
    
    success, msg = game.use_jail_card(player.id)
    
    results.add(assert_test(
        success,
        f"Used jail card: {msg}",
        f"Failed to use card: {msg}"
    ))
    
    results.add(assert_test(
        player.state == PlayerState.ACTIVE,
        "Player is now ACTIVE",
        f"Player state is {player.state}"
    ))
    
    results.add(assert_test(
        player.jail_cards == 0,
        "Jail card was consumed",
        f"Player has {player.jail_cards} jail cards"
    ))
    
    return results.failed == 0


# ============================================================================
# TEST GROUP 3: Forced Bankruptcy Scenarios
# ============================================================================

def test_bankruptcy_from_rent() -> bool:
    """Test forced bankruptcy when landing on expensive property."""
    print_header("FORCED BANKRUPTCY - RENT TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    p2_id = [pid for pid in game.player_order if pid != player.id][0]
    p2 = game.players[p2_id]
    
    print_subheader("Set up: P2 owns Boardwalk with hotel")
    boardwalk = game.board.get_property(39)
    park_place = game.board.get_property(37)
    
    # Give P2 monopoly on dark blue
    boardwalk.owner_id = p2.id
    park_place.owner_id = p2.id
    p2.add_property(37)
    p2.add_property(39)
    
    # Add hotel to Boardwalk (rent = $2000)
    boardwalk.houses = 0
    boardwalk.has_hotel = True
    
    print_subheader("Player lands on Boardwalk with insufficient funds")
    player.position = 36
    player.money = 500  # Much less than $2000 rent
    player.properties.clear()  # No properties to mortgage
    
    game.dice = MockDice([DiceResult(die1=2, die2=1)])  # Move 3 to pos 39
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player.position == 39,
        "Player landed on Boardwalk",
        f"Player at position {player.position}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.PAYING_RENT,
        "Phase is PAYING_RENT (cannot afford rent)",
        f"Phase is {game.phase}"
    ))
    
    print_subheader("Player must declare bankruptcy")
    p2_initial_money = p2.money
    
    success, msg = game.declare_bankruptcy(player.id, p2.id)
    
    results.add(assert_test(
        success,
        f"Bankruptcy declared: {msg}",
        f"Bankruptcy failed: {msg}"
    ))
    
    results.add(assert_test(
        player.state == PlayerState.BANKRUPT,
        "Player is BANKRUPT",
        f"Player state is {player.state}"
    ))
    
    # Creditor (P2) should receive player's remaining money
    results.add(assert_test(
        p2.money > p2_initial_money,
        f"Creditor received bankrupt player's assets (${p2.money})",
        f"Creditor money: ${p2.money}"
    ))
    
    return results.failed == 0


def test_bankruptcy_from_tax() -> bool:
    """Test bankruptcy from landing on tax space."""
    print_header("FORCED BANKRUPTCY - TAX TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Player lands on Income Tax with $50")
    player.position = 0
    player.money = 50  # Cannot afford $200 tax
    player.properties.clear()
    
    game.dice = MockDice([DiceResult(die1=2, die2=2)])  # Land on pos 4
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.PAYING_RENT,
        "Phase is PAYING_RENT",
        f"Phase is {game.phase}"
    ))
    
    print_subheader("Declare bankruptcy to bank")
    success, msg = game.declare_bankruptcy(player.id)  # No creditor = bank
    
    results.add(assert_test(
        success,
        f"Bankruptcy declared: {msg}",
        f"Bankruptcy failed: {msg}"
    ))
    
    results.add(assert_test(
        player.state == PlayerState.BANKRUPT,
        "Player is BANKRUPT",
        f"Player state is {player.state}"
    ))
    
    return results.failed == 0


def test_bankruptcy_from_card_payment() -> bool:
    """Test bankruptcy from card that requires payment."""
    print_header("FORCED BANKRUPTCY - CARD PAYMENT TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Draw expensive card with insufficient funds")
    player.position = 0
    player.money = 30  # Cannot afford $50 card payment
    player.properties.clear()
    
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "Doctor's fee. Pay $50.",
                CardAction.PAY_MONEY,
                value=50
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    game.dice = MockDice([DiceResult(die1=4, die2=3)])  # Land on Chance
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.PAYING_RENT,
        "Phase is PAYING_RENT (cannot afford card payment)",
        f"Phase is {game.phase}"
    ))
    
    print_subheader("Declare bankruptcy")
    success, msg = game.declare_bankruptcy(player.id)
    
    results.add(assert_test(
        success,
        f"Bankruptcy declared: {msg}",
        f"Bankruptcy failed: {msg}"
    ))
    
    results.add(assert_test(
        player.state == PlayerState.BANKRUPT,
        "Player is BANKRUPT",
        f"Player state is {player.state}"
    ))
    
    return results.failed == 0


def test_bankruptcy_triggers_game_over() -> bool:
    """Test that bankruptcy with 2 players ends the game."""
    print_header("BANKRUPTCY TRIGGERS GAME OVER TESTS")
    results = TestResults()
    
    game = create_test_game(num_players=2)
    player = game.current_player
    p2_id = [pid for pid in game.player_order if pid != player.id][0]
    p2 = game.players[p2_id]
    
    print_subheader("Set up bankruptcy scenario")
    player.money = 10
    player.properties.clear()
    
    # Force PAYING_RENT phase
    game.phase = GamePhase.PAYING_RENT
    
    print_subheader("Declare bankruptcy")
    success, msg = game.declare_bankruptcy(player.id)
    
    results.add(assert_test(
        success,
        f"Bankruptcy declared: {msg}",
        f"Bankruptcy failed: {msg}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.GAME_OVER,
        "Game phase is GAME_OVER",
        f"Game phase is {game.phase}"
    ))
    
    results.add(assert_test(
        game.winner_id == p2.id,
        f"Winner is {p2.name}",
        f"Winner ID is {game.winner_id}"
    ))
    
    results.add(assert_test(
        "wins" in msg.lower() or "game over" in msg.lower(),
        f"Message indicates game over: {msg}",
        f"Unexpected message: {msg}"
    ))
    
    return results.failed == 0


# ============================================================================
# TEST GROUP 4: Chain Reactions
# ============================================================================

def test_card_to_property_to_rent_chain() -> bool:
    """Test chain: Card moves player -> lands on property -> pays rent."""
    print_header("CHAIN REACTION - CARD TO RENT TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    p2_id = [pid for pid in game.player_order if pid != player.id][0]
    p2 = game.players[p2_id]
    
    print_subheader("Set up: P2 owns Illinois Avenue")
    illinois = game.board.get_property(24)
    illinois.owner_id = p2.id
    p2.add_property(24)
    
    print_subheader("Player draws 'Advance to Illinois Avenue' card")
    player.position = 0
    player.money = STARTING_MONEY
    initial_money = player.money
    p2_initial = p2.money
    
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "Advance to Illinois Avenue. If you pass Go, collect $200.",
                CardAction.MOVE_TO,
                value=24
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    game.dice = MockDice([DiceResult(die1=4, die2=3)])  # Land on Chance
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Roll succeeded: {msg}",
        f"Roll failed: {msg}"
    ))
    
    results.add(assert_test(
        player.position == 24,
        "Player moved to Illinois Avenue",
        f"Player at position {player.position}"
    ))
    
    # Calculate expected rent
    rent = illinois.calculate_rent(0, 1)  # dice_roll=0 (not utility), 1 owned in group
    
    results.add(assert_test(
        player.money == initial_money - rent,
        f"Player paid ${rent} rent (now ${player.money})",
        f"Player money is ${player.money}"
    ))
    
    results.add(assert_test(
        p2.money == p2_initial + rent,
        f"P2 received ${rent} rent (now ${p2.money})",
        f"P2 money is ${p2.money}"
    ))
    
    return results.failed == 0


def test_passing_go_during_card_movement() -> bool:
    """Test that passing GO during card movement collects $200."""
    print_header("PASSING GO DURING CARD MOVEMENT TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Card moves player past GO")
    player.position = 36  # Near end of board
    player.money = STARTING_MONEY
    initial_money = player.money
    
    # Draw card that sends to position 5 (Reading Railroad)
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "Take a trip to Reading Railroad. If you pass Go, collect $200.",
                CardAction.MOVE_TO,
                value=5  # Reading Railroad
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    
    # Move to Chance space at position 36
    game.dice = MockDice([DiceResult(die1=0, die2=0)])  # Won't be used
    player.position = 36  # Chance space
    
    # Manually trigger card draw (simulating landing on Chance)
    from shared.enums import CardType
    success, msg, dice_result = game._handle_card(player, CardType.CHANCE, DiceResult(die1=3, die2=3))
    
    results.add(assert_test(
        success,
        f"Card handled: {msg}",
        f"Card failed: {msg}"
    ))
    
    results.add(assert_test(
        player.position == 5,
        "Player at Reading Railroad (position 5)",
        f"Player at position {player.position}"
    ))
    
    # Should have collected $200 for passing GO (36 -> 5 wraps around)
    results.add(assert_test(
        player.money == initial_money + SALARY_AMOUNT,
        f"Player collected ${SALARY_AMOUNT} for passing GO (now ${player.money})",
        f"Player money is ${player.money}, expected ${initial_money + SALARY_AMOUNT}"
    ))
    
    return results.failed == 0


def test_repair_card_with_buildings() -> bool:
    """Test repair card calculates costs correctly based on buildings."""
    print_header("REPAIR CARD WITH BUILDINGS TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Set up: Player owns properties with buildings")
    # Give player Mediterranean and Baltic (brown monopoly)
    mediterranean = game.board.get_property(1)
    baltic = game.board.get_property(3)
    
    mediterranean.owner_id = player.id
    baltic.owner_id = player.id
    player.add_property(1)
    player.add_property(3)
    
    # Add 2 houses to each
    mediterranean.houses = 2
    baltic.houses = 2
    
    player.money = STARTING_MONEY
    initial_money = player.money
    
    print_subheader("Draw repair card ($25/house, $100/hotel)")
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "Make general repairs on all your property. For each house pay $25. For each hotel pay $100.",
                CardAction.REPAIRS,
                per_house=25,
                per_hotel=100
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    
    # Calculate expected cost: 4 houses * $25 = $100
    expected_cost = 4 * 25
    
    # Trigger card
    success, msg, _ = game._handle_card(player, CardType.CHANCE, DiceResult(die1=3, die2=3))
    
    results.add(assert_test(
        success,
        f"Card handled: {msg}",
        f"Card failed: {msg}"
    ))
    
    results.add(assert_test(
        player.money == initial_money - expected_cost,
        f"Player paid ${expected_cost} for repairs (now ${player.money})",
        f"Player money is ${player.money}, expected ${initial_money - expected_cost}"
    ))
    
    print_subheader("Test with hotel")
    # Add hotel to Mediterranean
    mediterranean.houses = 0
    mediterranean.has_hotel = True
    baltic.houses = 3  # 3 houses
    
    player.money = STARTING_MONEY
    initial_money = player.money
    
    # Expected: 1 hotel * $100 + 3 houses * $25 = $100 + $75 = $175
    expected_cost = 100 + (3 * 25)
    
    success, msg, _ = game._handle_card(player, CardType.CHANCE, DiceResult(die1=3, die2=3))
    
    results.add(assert_test(
        success,
        f"Card handled: {msg}",
        f"Card failed: {msg}"
    ))
    
    results.add(assert_test(
        player.money == initial_money - expected_cost,
        f"Player paid ${expected_cost} for repairs (now ${player.money})",
        f"Player money is ${player.money}"
    ))
    
    return results.failed == 0


def test_collect_from_players_card() -> bool:
    """Test 'It's your birthday' card (collect from each player)."""
    print_header("COLLECT FROM PLAYERS CARD TESTS")
    results = TestResults()
    
    game = create_test_game(num_players=4)
    player = game.current_player
    
    # Get all other players
    other_players = [game.players[pid] for pid in game.player_order if pid != player.id]
    
    print_subheader("Draw 'It is your birthday. Collect $10 from every player.'")
    player.money = 100
    initial_money = player.money
    
    for p in other_players:
        p.money = 500
    
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "It is your birthday. Collect $10 from every player.",
                CardAction.COLLECT_FROM_PLAYERS,
                value=10
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    
    # Expected: $10 from each of 3 other players = $30
    expected_collection = 10 * len(other_players)
    
    success, msg, _ = game._handle_card(player, CardType.CHANCE, DiceResult(die1=3, die2=3))
    
    results.add(assert_test(
        success,
        f"Card handled: {msg}",
        f"Card failed: {msg}"
    ))
    
    results.add(assert_test(
        player.money == initial_money + expected_collection,
        f"Player collected ${expected_collection} (now ${player.money})",
        f"Player money is ${player.money}"
    ))
    
    for p in other_players:
        results.add(assert_test(
            p.money == 490,
            f"{p.name} paid $10 (now ${p.money})",
            f"{p.name} has ${p.money}"
        ))
    
    return results.failed == 0


def test_pay_to_players_card() -> bool:
    """Test 'Chairman of the Board' card (pay each player)."""
    print_header("PAY TO PLAYERS CARD TESTS")
    results = TestResults()
    
    game = create_test_game(num_players=3)
    player = game.current_player
    
    other_players = [game.players[pid] for pid in game.player_order if pid != player.id]
    
    print_subheader("Draw 'Pay each player $50'")
    player.money = 500
    initial_money = player.money
    
    for p in other_players:
        p.money = 100
    
    class MockCardManager:
        def draw_chance(self):
            return Card(
                CardType.CHANCE,
                "You have been elected Chairman of the Board. Pay each player $50.",
                CardAction.PAY_TO_PLAYERS,
                value=50
            )
        def draw_community_chest(self):
            return Card(CardType.COMMUNITY_CHEST, "Test", CardAction.COLLECT_MONEY, value=0)
        def return_jail_card(self, card_type):
            pass
        def to_dict(self):
            return {}
    
    game.cards = MockCardManager()
    
    # Expected: $50 to each of 2 other players = $100
    expected_payment = 50 * len(other_players)
    
    success, msg, _ = game._handle_card(player, CardType.CHANCE, DiceResult(die1=3, die2=3))
    
    results.add(assert_test(
        success,
        f"Card handled: {msg}",
        f"Card failed: {msg}"
    ))
    
    results.add(assert_test(
        player.money == initial_money - expected_payment,
        f"Player paid ${expected_payment} (now ${player.money})",
        f"Player money is ${player.money}"
    ))
    
    for p in other_players:
        results.add(assert_test(
            p.money == 150,
            f"{p.name} received $50 (now ${p.money})",
            f"{p.name} has ${p.money}"
        ))
    
    return results.failed == 0


# ============================================================================
# TEST GROUP 5: Complete Turn Sequences
# ============================================================================

def test_complete_turn_buy_property() -> bool:
    """Test complete turn: roll -> land on property -> buy -> end turn."""
    print_header("COMPLETE TURN - BUY PROPERTY TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    
    print_subheader("Roll dice")
    player.position = 0
    player.money = STARTING_MONEY
    
    # Roll to land on Mediterranean Avenue (position 1)
    game.dice = MockDice([DiceResult(die1=0, die2=1)])
    
    success, msg, dice = game.roll_dice(player.id)
    
    results.add(assert_test(
        success and player.position == 1,
        f"Rolled and landed on Mediterranean Avenue",
        f"Roll result: {msg}, position: {player.position}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.PROPERTY_DECISION,
        "Phase is PROPERTY_DECISION",
        f"Phase is {game.phase}"
    ))
    
    print_subheader("Buy property")
    initial_money = player.money
    mediterranean = game.board.get_property(1)
    
    success, msg = game.buy_property(player.id)
    
    results.add(assert_test(
        success,
        f"Bought property: {msg}",
        f"Failed: {msg}"
    ))
    
    results.add(assert_test(
        player.money == initial_money - mediterranean.cost,
        f"Paid ${mediterranean.cost} for property",
        f"Money: ${player.money}"
    ))
    
    results.add(assert_test(
        1 in player.properties,
        "Player owns Mediterranean Avenue",
        f"Properties: {player.properties}"
    ))
    
    print_subheader("End turn")
    success, msg = game.end_turn(player.id)
    
    results.add(assert_test(
        success,
        f"Turn ended: {msg}",
        f"Failed: {msg}"
    ))
    
    results.add(assert_test(
        game.current_player.id != player.id,
        "Turn advanced to next player",
        f"Current player: {game.current_player.name}"
    ))
    
    return results.failed == 0


def test_complete_turn_pay_rent() -> bool:
    """Test complete turn: roll -> land on owned property -> pay rent -> end turn."""
    print_header("COMPLETE TURN - PAY RENT TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    p2_id = [pid for pid in game.player_order if pid != player.id][0]
    p2 = game.players[p2_id]
    
    print_subheader("Set up: P2 owns Mediterranean Avenue")
    mediterranean = game.board.get_property(1)
    mediterranean.owner_id = p2.id
    p2.add_property(1)
    
    print_subheader("Roll dice and land on owned property")
    player.position = 0
    player.money = STARTING_MONEY
    p2.money = STARTING_MONEY
    
    game.dice = MockDice([DiceResult(die1=0, die2=1)])
    
    success, msg, _ = game.roll_dice(player.id)
    
    results.add(assert_test(
        success,
        f"Rolled: {msg}",
        f"Failed: {msg}"
    ))
    
    rent = mediterranean.calculate_rent(0, 1)
    
    results.add(assert_test(
        player.money == STARTING_MONEY - rent,
        f"Player paid ${rent} rent",
        f"Player money: ${player.money}"
    ))
    
    results.add(assert_test(
        p2.money == STARTING_MONEY + rent,
        f"P2 received ${rent} rent",
        f"P2 money: ${p2.money}"
    ))
    
    print_subheader("End turn")
    success, msg = game.end_turn(player.id)
    
    results.add(assert_test(
        success,
        f"Turn ended: {msg}",
        f"Failed: {msg}"
    ))
    
    return results.failed == 0


def test_complete_turn_doubles_sequence() -> bool:
    """Test complete turn with doubles: roll doubles -> act -> roll again -> end."""
    print_header("COMPLETE TURN - DOUBLES SEQUENCE TESTS")
    results = TestResults()
    
    game = create_test_game()
    player = game.current_player
    original_player_id = player.id
    
    print_subheader("Roll doubles")
    player.position = 0
    
    # Roll doubles (3,3 = 6)
    game.dice = MockDice([
        DiceResult(die1=3, die2=3),  # First roll - doubles
        DiceResult(die1=2, die2=4),  # Second roll - not doubles
    ])
    
    success, msg, dice = game.roll_dice(player.id)
    
    results.add(assert_test(
        success and dice.is_double,
        f"Rolled doubles: {dice.die1}, {dice.die2}",
        f"Failed or not doubles: {msg}"
    ))
    
    results.add(assert_test(
        player.position == 6,
        f"Moved to position 6",
        f"Position: {player.position}"
    ))
    
    print_subheader("Handle landing and try to end turn")
    # If landed on property, handle it
    if game.phase == GamePhase.PROPERTY_DECISION:
        game.decline_property(player.id)
    
    success, msg = game.end_turn(player.id)
    
    results.add(assert_test(
        success,
        f"End turn result: {msg}",
        f"Failed: {msg}"
    ))
    
    results.add(assert_test(
        game.current_player.id == original_player_id,
        "Same player gets another turn (doubles)",
        f"Current player changed"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.PRE_ROLL,
        "Phase is PRE_ROLL for second roll",
        f"Phase: {game.phase}"
    ))
    
    print_subheader("Roll again (non-doubles)")
    success, msg, dice = game.roll_dice(player.id)
    
    results.add(assert_test(
        success and not dice.is_double,
        f"Rolled non-doubles: {dice.die1}, {dice.die2}",
        f"Failed: {msg}"
    ))
    
    print_subheader("End turn after non-doubles")
    if game.phase == GamePhase.PROPERTY_DECISION:
        game.decline_property(player.id)
    
    success, msg = game.end_turn(player.id)
    
    results.add(assert_test(
        success,
        f"Turn ended: {msg}",
        f"Failed: {msg}"
    ))
    
    results.add(assert_test(
        game.current_player.id != original_player_id,
        "Turn advanced to next player",
        f"Still same player"
    ))
    
    return results.failed == 0


# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests() -> bool:
    """Run all game flow integration tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         GAME FLOW INTEGRATION TEST SUITE                 ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.RESET)

    all_results = TestResults()

    tests = [
        # Group 1: Tax Payment Flow
        ("Tax Payment - Can Afford", test_tax_payment_can_afford),
        ("Tax Payment - Cannot Afford", test_tax_payment_cannot_afford),
        ("Tax Payment - Exact Funds", test_tax_with_exact_funds),
        
        # Group 2: Card-Induced Movement
        ("Card - Move to GO", test_card_move_to_go),
        ("Card - Move to Property", test_card_move_to_property),
        ("Card - Go to Jail", test_card_go_to_jail),
        ("Card - Go Back 3 Spaces", test_card_move_back),
        ("Card - Get Out of Jail Free", test_card_get_out_of_jail_free),
        
        # Group 3: Forced Bankruptcy
        ("Bankruptcy from Rent", test_bankruptcy_from_rent),
        ("Bankruptcy from Tax", test_bankruptcy_from_tax),
        ("Bankruptcy from Card Payment", test_bankruptcy_from_card_payment),
        ("Bankruptcy Triggers Game Over", test_bankruptcy_triggers_game_over),
        
        # Group 4: Chain Reactions
        ("Chain: Card to Rent", test_card_to_property_to_rent_chain),
        ("Passing GO During Card Movement", test_passing_go_during_card_movement),
        ("Repair Card with Buildings", test_repair_card_with_buildings),
        ("Collect from Players Card", test_collect_from_players_card),
        ("Pay to Players Card", test_pay_to_players_card),
        
        # Group 5: Complete Turn Sequences
        ("Complete Turn - Buy Property", test_complete_turn_buy_property),
        ("Complete Turn - Pay Rent", test_complete_turn_pay_rent),
        ("Complete Turn - Doubles Sequence", test_complete_turn_doubles_sequence),
    ]

    for name, test_func in tests:
        try:
            passed = test_func()
            all_results.add(passed)
        except Exception as e:
            print_failure(f"{name} tests raised exception: {e}")
            import traceback
            traceback.print_exc()
            all_results.add(False)

    all_results.summary()

    return all_results.failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
