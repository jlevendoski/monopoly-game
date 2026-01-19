"""
Comprehensive tests for bankruptcy mechanics.

Tests all bankruptcy scenarios including:
- Bankruptcy to bank (no creditor)
- Bankruptcy to another player (creditor)
- Asset transfer
- Game over detection
- Turn advancement after bankruptcy

Run from project root: python -m pytest tests/test_game_engine/test_bankruptcy.py -v
Or run directly: python tests/test_game_engine/test_bankruptcy.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.game_engine import Game, Player
from shared.enums import GamePhase, PlayerState
from shared.constants import STARTING_MONEY


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


def create_test_game() -> Game:
    """Create a game with two players for testing."""
    game = Game(name="Bankruptcy Test Game")
    game.add_player("Alice")
    game.add_player("Bob")
    game.start_game()
    return game


def create_three_player_game() -> Game:
    """Create a game with three players for testing."""
    game = Game(name="Bankruptcy Test Game")
    game.add_player("Alice")
    game.add_player("Bob")
    game.add_player("Charlie")
    game.start_game()
    return game


def test_bankruptcy_to_bank() -> bool:
    """Test bankruptcy when no specific creditor (e.g., taxes, cards)."""
    print_header("BANKRUPTCY TO BANK TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Give Alice some properties
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    alice.money = 0

    print_subheader("Declare bankruptcy to bank")
    success, msg = game.declare_bankruptcy(alice.id, creditor_id=None)
    
    results.add(assert_test(
        success,
        f"Bankruptcy declared: {msg}",
        f"Bankruptcy failed: {msg}"
    ))
    
    results.add(assert_test(
        alice.state == PlayerState.BANKRUPT,
        "Alice is now BANKRUPT",
        f"Alice state is {alice.state}"
    ))

    print_subheader("Properties returned to bank")
    results.add(assert_test(
        med.owner_id is None,
        "Mediterranean returned to bank",
        f"Mediterranean owner: {med.owner_id}"
    ))
    
    results.add(assert_test(
        baltic.owner_id is None,
        "Baltic returned to bank",
        f"Baltic owner: {baltic.owner_id}"
    ))

    print_subheader("Properties unmortgaged when returned")
    # In a fresh game, test that mortgaged properties get unmortgaged
    game2 = create_test_game()
    alice2 = game2.current_player
    
    med2 = game2.board.get_property(1)
    med2.owner_id = alice2.id
    med2.is_mortgaged = True
    alice2.add_property(1)
    alice2.money = 0
    
    game2.declare_bankruptcy(alice2.id, creditor_id=None)
    
    results.add(assert_test(
        not med2.is_mortgaged,
        "Property unmortgaged when returned to bank",
        f"Property still mortgaged: {med2.is_mortgaged}"
    ))

    return results.failed == 0


def test_bankruptcy_to_player() -> bool:
    """Test bankruptcy when owing another player rent."""
    print_header("BANKRUPTCY TO PLAYER TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Give Alice properties and jail cards
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    alice.jail_cards = 2
    alice.money = 50
    
    bob_money_before = bob.money
    bob_properties_before = len(bob.properties)
    bob_jail_cards_before = bob.jail_cards

    print_subheader("Declare bankruptcy to another player")
    success, msg = game.declare_bankruptcy(alice.id, creditor_id=bob.id)
    
    results.add(assert_test(
        success,
        f"Bankruptcy declared: {msg}",
        f"Bankruptcy failed: {msg}"
    ))

    print_subheader("Money transferred to creditor")
    results.add(assert_test(
        bob.money == bob_money_before + 50,
        f"Bob received Alice's money: ${bob.money}",
        f"Bob money incorrect: ${bob.money}"
    ))

    print_subheader("Properties transferred to creditor")
    results.add(assert_test(
        med.owner_id == bob.id,
        "Mediterranean transferred to Bob",
        f"Mediterranean owner: {med.owner_id}"
    ))
    
    results.add(assert_test(
        baltic.owner_id == bob.id,
        "Baltic transferred to Bob",
        f"Baltic owner: {baltic.owner_id}"
    ))
    
    results.add(assert_test(
        1 in bob.properties and 3 in bob.properties,
        "Properties in Bob's list",
        f"Bob's properties: {bob.properties}"
    ))

    print_subheader("Jail cards transferred to creditor")
    results.add(assert_test(
        bob.jail_cards == bob_jail_cards_before + 2,
        f"Bob received jail cards: {bob.jail_cards}",
        f"Bob jail cards: {bob.jail_cards}"
    ))

    return results.failed == 0


def test_buildings_sold_on_bankruptcy_to_bank() -> bool:
    """Test that buildings are sold when going bankrupt to bank."""
    print_header("BUILDINGS SOLD ON BANKRUPTCY TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player

    # Give Alice monopoly with buildings
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    
    med.houses = 3
    baltic.houses = 2
    game.rules.houses_available -= 5  # Reflect houses used
    
    alice.money = 0
    houses_before = game.rules.houses_available

    print_subheader("Buildings removed on bankruptcy to bank")
    game.declare_bankruptcy(alice.id, creditor_id=None)
    
    results.add(assert_test(
        med.houses == 0,
        "Mediterranean houses removed",
        f"Mediterranean houses: {med.houses}"
    ))
    
    results.add(assert_test(
        baltic.houses == 0,
        "Baltic houses removed",
        f"Baltic houses: {baltic.houses}"
    ))

    print_subheader("Houses returned to bank supply")
    results.add(assert_test(
        game.rules.houses_available == houses_before + 5,
        f"Houses returned: {game.rules.houses_available}",
        f"Houses should be {houses_before + 5}"
    ))

    return results.failed == 0


def test_game_over_on_bankruptcy() -> bool:
    """Test that game ends when only one player remains."""
    print_header("GAME OVER ON BANKRUPTCY TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    alice.money = 0

    print_subheader("Game over when one player goes bankrupt (2-player)")
    success, msg = game.declare_bankruptcy(alice.id)
    
    results.add(assert_test(
        game.is_game_over,
        "Game is over",
        f"Game should be over"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.GAME_OVER,
        "Phase is GAME_OVER",
        f"Phase is {game.phase}"
    ))
    
    results.add(assert_test(
        game.winner_id == bob.id,
        f"Bob is the winner",
        f"Winner is {game.winner_id}"
    ))

    return results.failed == 0


def test_game_continues_with_remaining_players() -> bool:
    """Test that game continues with 3+ players after one bankruptcy."""
    print_header("GAME CONTINUES WITH REMAINING PLAYERS TESTS")
    results = TestResults()

    game = create_three_player_game()
    players = list(game.players.values())
    alice = players[0]
    bob = players[1]
    charlie = players[2]

    alice.money = 0

    print_subheader("Game continues after one bankruptcy (3-player)")
    game.declare_bankruptcy(alice.id)
    
    results.add(assert_test(
        not game.is_game_over,
        "Game is NOT over",
        f"Game should continue"
    ))
    
    results.add(assert_test(
        game.phase != GamePhase.GAME_OVER,
        "Phase is not GAME_OVER",
        f"Phase is {game.phase}"
    ))
    
    active_count = len([p for p in game.players.values() if p.state != PlayerState.BANKRUPT])
    results.add(assert_test(
        active_count == 2,
        f"Two players remain active",
        f"Active players: {active_count}"
    ))

    print_subheader("Second bankruptcy ends game")
    bob.money = 0
    game.declare_bankruptcy(bob.id)
    
    results.add(assert_test(
        game.is_game_over,
        "Game is now over",
        f"Game should be over"
    ))
    
    results.add(assert_test(
        game.winner_id == charlie.id,
        f"Charlie is the winner",
        f"Winner is {game.winner_id}"
    ))

    return results.failed == 0


def test_turn_advances_after_current_player_bankruptcy() -> bool:
    """Test that turn advances when current player goes bankrupt."""
    print_header("TURN ADVANCEMENT AFTER BANKRUPTCY TESTS")
    results = TestResults()

    game = create_three_player_game()
    current = game.current_player
    current.money = 0
    current_id = current.id
    current_index = game.current_player_index

    print_subheader("Turn advances after current player bankruptcy")
    game.declare_bankruptcy(current_id)
    
    results.add(assert_test(
        game.current_player.id != current_id,
        f"Turn moved to different player",
        f"Current player should have changed"
    ))
    
    results.add(assert_test(
        game.current_player.state == PlayerState.ACTIVE,
        "New current player is ACTIVE",
        f"Current player state: {game.current_player.state}"
    ))

    return results.failed == 0


def test_bankrupt_player_skipped_in_turn_order() -> bool:
    """Test that bankrupt players are skipped in turn rotation."""
    print_header("BANKRUPT PLAYER SKIPPED TESTS")
    results = TestResults()

    game = create_three_player_game()
    players = list(game.players.values())
    
    # Make second player in order go bankrupt
    second_player_id = game.player_order[1]
    game.players[second_player_id].money = 0
    game.players[second_player_id].declare_bankruptcy()

    print_subheader("Bankrupt player skipped in turn rotation")
    # Simulate turns
    seen_players = []
    for _ in range(6):  # 6 turns should never hit bankrupt player
        if game.current_player:
            seen_players.append(game.current_player.id)
            game._advance_turn()
    
    results.add(assert_test(
        second_player_id not in seen_players,
        "Bankrupt player never got a turn",
        f"Bankrupt player was in turn order: {seen_players}"
    ))

    return results.failed == 0


def test_calculate_total_assets() -> bool:
    """Test total asset calculation for bankruptcy decisions."""
    print_header("TOTAL ASSETS CALCULATION TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player

    print_subheader("Cash only")
    alice.money = 500
    alice.properties.clear()
    
    total = game.rules.calculate_total_assets(alice)
    
    results.add(assert_test(
        total == 500,
        f"Total assets (cash only): ${total}",
        f"Should be $500"
    ))

    print_subheader("Cash plus unmortgaged properties")
    med = game.board.get_property(1)
    med.owner_id = alice.id
    med.is_mortgaged = False
    alice.add_property(1)
    
    # Mediterranean mortgage value is $30 (half of $60 cost)
    total = game.rules.calculate_total_assets(alice)
    
    results.add(assert_test(
        total == 500 + 30,
        f"Total assets (with property): ${total}",
        f"Should be $530"
    ))

    print_subheader("Mortgaged properties don't add value")
    med.is_mortgaged = True
    
    total = game.rules.calculate_total_assets(alice)
    
    results.add(assert_test(
        total == 500,
        f"Total assets (mortgaged property): ${total}",
        f"Should be $500 (mortgaged adds nothing)"
    ))

    print_subheader("Buildings add half value")
    med.is_mortgaged = False
    med.houses = 2
    # Mediterranean house cost is $50, half is $25 per house
    
    total = game.rules.calculate_total_assets(alice)
    
    results.add(assert_test(
        total == 500 + 30 + (2 * 25),  # Cash + mortgage value + buildings
        f"Total assets (with houses): ${total}",
        f"Should be ${500 + 30 + 50}"
    ))

    return results.failed == 0


def test_can_player_pay() -> bool:
    """Test checking if player can pay through liquidation."""
    print_header("CAN PLAYER PAY TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player

    print_subheader("Can pay with cash alone")
    alice.money = 100
    
    can_pay = game.rules.can_player_pay(alice, 50)
    
    results.add(assert_test(
        can_pay,
        "Can pay $50 with $100 cash",
        "Should be able to pay"
    ))

    print_subheader("Cannot pay more than total assets")
    alice.money = 50
    alice.properties.clear()
    
    can_pay = game.rules.can_player_pay(alice, 100)
    
    results.add(assert_test(
        not can_pay,
        "Cannot pay $100 with only $50",
        "Should not be able to pay"
    ))

    print_subheader("Can pay by liquidating assets")
    med = game.board.get_property(1)
    med.owner_id = alice.id
    med.is_mortgaged = False
    alice.add_property(1)
    alice.money = 50
    # Total assets: $50 + $30 (mortgage value) = $80
    
    can_pay = game.rules.can_player_pay(alice, 80)
    
    results.add(assert_test(
        can_pay,
        "Can pay $80 by mortgaging",
        "Should be able to pay with liquidation"
    ))
    
    can_pay = game.rules.can_player_pay(alice, 81)
    
    results.add(assert_test(
        not can_pay,
        "Cannot pay $81 (exceeds total assets)",
        "Should not be able to pay"
    ))

    return results.failed == 0


def test_player_state_after_bankruptcy() -> bool:
    """Test player state is properly updated after bankruptcy."""
    print_header("PLAYER STATE AFTER BANKRUPTCY TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    alice.money = 100
    alice.jail_cards = 2
    
    med = game.board.get_property(1)
    med.owner_id = alice.id
    alice.add_property(1)

    print_subheader("Player state after bankruptcy")
    game.declare_bankruptcy(alice.id)
    
    results.add(assert_test(
        alice.state == PlayerState.BANKRUPT,
        "Player state is BANKRUPT",
        f"State is {alice.state}"
    ))
    
    results.add(assert_test(
        len(alice.properties) == 0,
        "Player has no properties",
        f"Properties: {alice.properties}"
    ))

    # Note: When going bankrupt to BANK, money and jail cards remain
    # on the player (they're effectively lost to the game).
    # When going bankrupt to a CREDITOR, they transfer to that player.
    # This test verifies the current implementation.

    return results.failed == 0


def run_all_tests() -> bool:
    """Run all bankruptcy tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              BANKRUPTCY MECHANICS TEST SUITE             ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.RESET)

    all_results = TestResults()

    tests = [
        ("Bankruptcy to Bank", test_bankruptcy_to_bank),
        ("Bankruptcy to Player", test_bankruptcy_to_player),
        ("Buildings Sold on Bankruptcy", test_buildings_sold_on_bankruptcy_to_bank),
        ("Game Over on Bankruptcy", test_game_over_on_bankruptcy),
        ("Game Continues with Remaining", test_game_continues_with_remaining_players),
        ("Turn Advances After Bankruptcy", test_turn_advances_after_current_player_bankruptcy),
        ("Bankrupt Player Skipped", test_bankrupt_player_skipped_in_turn_order),
        ("Calculate Total Assets", test_calculate_total_assets),
        ("Can Player Pay", test_can_player_pay),
        ("Player State After Bankruptcy", test_player_state_after_bankruptcy),
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
