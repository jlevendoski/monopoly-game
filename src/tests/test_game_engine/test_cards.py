"""
Comprehensive tests for Chance and Community Chest card actions.

These tests verify that each card action type works correctly,
including edge cases like position wrapping and insufficient funds.

Run from project root: python -m pytest tests/test_game_engine/test_cards.py -v
Or run directly: python tests/test_game_engine/test_cards.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.game_engine import Game, Player, Board, CardManager
from server.game_engine.cards import Card, CardAction, CHANCE_CARDS, COMMUNITY_CHEST_CARDS
from server.game_engine.dice import Dice, DiceResult
from shared.enums import GamePhase, PlayerState, CardType
from shared.constants import STARTING_MONEY, SALARY_AMOUNT, JAIL_POSITION


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
    game = Game(name="Card Test Game")
    game.add_player("Alice")
    game.add_player("Bob")
    game.start_game()
    return game


def test_card_collect_money() -> bool:
    """Test COLLECT_MONEY card action."""
    print_header("COLLECT_MONEY CARD TESTS")
    results = TestResults()

    game = create_test_game()
    player = game.current_player

    print_subheader("Bank pays dividend")
    old_money = player.money
    
    # Create a collect money card
    card = Card(
        CardType.CHANCE,
        "Bank pays you dividend of $50.",
        CardAction.COLLECT_MONEY,
        value=50
    )
    
    # Execute the card (simulating what _execute_card does)
    player.add_money(card.value)
    
    results.add(assert_test(
        player.money == old_money + 50,
        f"Player collected $50: ${player.money}",
        f"Money incorrect: ${player.money} (expected ${old_money + 50})"
    ))

    print_subheader("Large collection amount")
    old_money = player.money
    card = Card(
        CardType.COMMUNITY_CHEST,
        "Bank error in your favor. Collect $200.",
        CardAction.COLLECT_MONEY,
        value=200
    )
    player.add_money(card.value)
    
    results.add(assert_test(
        player.money == old_money + 200,
        f"Player collected $200: ${player.money}",
        f"Money incorrect: ${player.money}"
    ))

    return results.failed == 0


def test_card_pay_money() -> bool:
    """Test PAY_MONEY card action."""
    print_header("PAY_MONEY CARD TESTS")
    results = TestResults()

    game = create_test_game()
    player = game.current_player

    print_subheader("Pay small fine")
    old_money = player.money
    
    card = Card(
        CardType.CHANCE,
        "Speeding fine $15.",
        CardAction.PAY_MONEY,
        value=15
    )
    
    if player.can_afford(card.value):
        player.remove_money(card.value)
    
    results.add(assert_test(
        player.money == old_money - 15,
        f"Player paid $15: ${player.money}",
        f"Money incorrect: ${player.money}"
    ))

    print_subheader("Pay larger fee")
    old_money = player.money
    card = Card(
        CardType.COMMUNITY_CHEST,
        "Pay hospital fees of $100.",
        CardAction.PAY_MONEY,
        value=100
    )
    
    if player.can_afford(card.value):
        player.remove_money(card.value)
    
    results.add(assert_test(
        player.money == old_money - 100,
        f"Player paid $100: ${player.money}",
        f"Money incorrect: ${player.money}"
    ))

    print_subheader("Cannot afford payment")
    player.money = 30  # Set low money
    card = Card(
        CardType.COMMUNITY_CHEST,
        "Pay hospital fees of $100.",
        CardAction.PAY_MONEY,
        value=100
    )
    
    can_pay = player.can_afford(card.value)
    
    results.add(assert_test(
        not can_pay,
        "Player correctly cannot afford $100",
        "Player should not be able to afford $100"
    ))

    return results.failed == 0


def test_card_move_to_position() -> bool:
    """Test MOVE_TO card action with specific positions."""
    print_header("MOVE_TO CARD TESTS")
    results = TestResults()

    game = create_test_game()
    player = game.current_player

    print_subheader("Advance to GO")
    player.position = 15
    old_money = player.money
    
    card = Card(
        CardType.CHANCE,
        "Advance to Go (Collect $200)",
        CardAction.MOVE_TO,
        value=0
    )
    
    # Move to GO and collect salary
    player.move_to(card.value)
    
    results.add(assert_test(
        player.position == 0,
        f"Player moved to GO (position 0)",
        f"Player at wrong position: {player.position}"
    ))

    print_subheader("Advance to Illinois Avenue (position 24)")
    player.position = 5
    old_money = player.money
    
    card = Card(
        CardType.CHANCE,
        "Advance to Illinois Avenue. If you pass Go, collect $200.",
        CardAction.MOVE_TO,
        value=24
    )
    
    player.move_to(card.value)
    
    results.add(assert_test(
        player.position == 24,
        f"Player moved to Illinois Avenue (position 24)",
        f"Player at wrong position: {player.position}"
    ))

    print_subheader("Advance to Boardwalk (position 39)")
    player.position = 10
    
    card = Card(
        CardType.CHANCE,
        "Advance to Boardwalk.",
        CardAction.MOVE_TO,
        value=39
    )
    
    player.move_to(card.value)
    
    results.add(assert_test(
        player.position == 39,
        f"Player moved to Boardwalk (position 39)",
        f"Player at wrong position: {player.position}"
    ))

    print_subheader("Move passing GO collects $200")
    player.position = 35
    old_money = player.money
    
    card = Card(
        CardType.CHANCE,
        "Advance to St. Charles Place. If you pass Go, collect $200.",
        CardAction.MOVE_TO,
        value=11
    )
    
    # move_to with collect_go=True should collect GO salary when passing
    passed_go = player.move_to(card.value, collect_go=True)
    
    results.add(assert_test(
        player.position == 11,
        f"Player moved to St. Charles Place (position 11)",
        f"Player at wrong position: {player.position}"
    ))
    
    results.add(assert_test(
        passed_go and player.money == old_money + SALARY_AMOUNT,
        f"Player collected ${SALARY_AMOUNT} passing GO",
        f"GO salary not collected correctly: ${player.money} (expected ${old_money + SALARY_AMOUNT})"
    ))

    return results.failed == 0


def test_card_nearest_utility() -> bool:
    """Test MOVE_TO with value=-1 (nearest utility)."""
    print_header("NEAREST UTILITY CARD TESTS")
    results = TestResults()

    game = create_test_game()
    player = game.current_player

    # Utilities are at positions 12 (Electric Company) and 28 (Water Works)
    
    print_subheader("From position 7 (Chance) - nearest is Electric Company (12)")
    player.position = 7
    
    nearest = game.rules.get_nearest_utility(player.position)
    
    results.add(assert_test(
        nearest == 12,
        f"Nearest utility from position 7 is 12 (Electric Company)",
        f"Wrong nearest utility: {nearest}"
    ))

    print_subheader("From position 22 (Chance) - nearest is Water Works (28)")
    player.position = 22
    
    nearest = game.rules.get_nearest_utility(player.position)
    
    results.add(assert_test(
        nearest == 28,
        f"Nearest utility from position 22 is 28 (Water Works)",
        f"Wrong nearest utility: {nearest}"
    ))

    print_subheader("From position 36 (Chance) - wraps to Electric Company (12)")
    player.position = 36
    
    nearest = game.rules.get_nearest_utility(player.position)
    
    results.add(assert_test(
        nearest == 12,
        f"Nearest utility from position 36 is 12 (wraps around)",
        f"Wrong nearest utility: {nearest}"
    ))

    print_subheader("From position 13 - nearest is Water Works (28)")
    player.position = 13
    
    nearest = game.rules.get_nearest_utility(player.position)
    
    results.add(assert_test(
        nearest == 28,
        f"Nearest utility from position 13 is 28",
        f"Wrong nearest utility: {nearest}"
    ))

    return results.failed == 0


def test_card_nearest_railroad() -> bool:
    """Test MOVE_TO with value=-2 (nearest railroad)."""
    print_header("NEAREST RAILROAD CARD TESTS")
    results = TestResults()

    game = create_test_game()
    player = game.current_player

    # Railroads are at positions 5, 15, 25, 35
    
    print_subheader("From position 7 (Chance) - nearest is Pennsylvania RR (15)")
    player.position = 7
    
    nearest = game.rules.get_nearest_railroad(player.position)
    
    results.add(assert_test(
        nearest == 15,
        f"Nearest railroad from position 7 is 15 (Pennsylvania RR)",
        f"Wrong nearest railroad: {nearest}"
    ))

    print_subheader("From position 22 (Chance) - nearest is B&O RR (25)")
    player.position = 22
    
    nearest = game.rules.get_nearest_railroad(player.position)
    
    results.add(assert_test(
        nearest == 25,
        f"Nearest railroad from position 22 is 25 (B&O RR)",
        f"Wrong nearest railroad: {nearest}"
    ))

    print_subheader("From position 36 (Chance) - wraps to Reading RR (5)")
    player.position = 36
    
    nearest = game.rules.get_nearest_railroad(player.position)
    
    results.add(assert_test(
        nearest == 5,
        f"Nearest railroad from position 36 is 5 (wraps to Reading RR)",
        f"Wrong nearest railroad: {nearest}"
    ))

    print_subheader("From position 3 - nearest is Reading RR (5)")
    player.position = 3
    
    nearest = game.rules.get_nearest_railroad(player.position)
    
    results.add(assert_test(
        nearest == 5,
        f"Nearest railroad from position 3 is 5",
        f"Wrong nearest railroad: {nearest}"
    ))

    print_subheader("From position 30 - nearest is Short Line (35)")
    player.position = 30
    
    nearest = game.rules.get_nearest_railroad(player.position)
    
    results.add(assert_test(
        nearest == 35,
        f"Nearest railroad from position 30 is 35 (Short Line)",
        f"Wrong nearest railroad: {nearest}"
    ))

    return results.failed == 0


def test_card_move_back() -> bool:
    """Test MOVE_BACK card action."""
    print_header("MOVE_BACK CARD TESTS")
    results = TestResults()

    game = create_test_game()
    player = game.current_player

    print_subheader("Go back 3 spaces from position 10")
    player.position = 10
    
    card = Card(
        CardType.CHANCE,
        "Go Back 3 Spaces.",
        CardAction.MOVE_BACK,
        value=3
    )
    
    new_pos = (player.position - card.value) % 40
    player.move_to(new_pos, collect_go=False)
    
    results.add(assert_test(
        player.position == 7,
        f"Player moved back to position 7",
        f"Player at wrong position: {player.position}"
    ))

    print_subheader("Go back 3 spaces from position 2 (wraps to 39)")
    player.position = 2
    
    new_pos = (player.position - 3) % 40
    player.move_to(new_pos, collect_go=False)
    
    results.add(assert_test(
        player.position == 39,
        f"Player wrapped around to position 39",
        f"Player at wrong position: {player.position}"
    ))

    print_subheader("Go back 3 spaces from position 1 (wraps to 38)")
    player.position = 1
    
    new_pos = (player.position - 3) % 40
    player.move_to(new_pos, collect_go=False)
    
    results.add(assert_test(
        player.position == 38,
        f"Player wrapped around to position 38",
        f"Player at wrong position: {player.position}"
    ))

    return results.failed == 0


def test_card_go_to_jail() -> bool:
    """Test GO_TO_JAIL card action."""
    print_header("GO_TO_JAIL CARD TESTS")
    results = TestResults()

    game = create_test_game()
    player = game.current_player

    print_subheader("Go to Jail card")
    player.position = 22
    old_money = player.money
    
    card = Card(
        CardType.CHANCE,
        "Go to Jail. Go directly to Jail, do not pass Go, do not collect $200.",
        CardAction.GO_TO_JAIL
    )
    
    player.send_to_jail()
    
    results.add(assert_test(
        player.position == JAIL_POSITION,
        f"Player sent to jail (position {JAIL_POSITION})",
        f"Player at wrong position: {player.position}"
    ))
    
    results.add(assert_test(
        player.state == PlayerState.IN_JAIL,
        "Player state is IN_JAIL",
        f"Player state is {player.state}"
    ))
    
    results.add(assert_test(
        player.money == old_money,
        "Player did not collect GO salary",
        f"Player money changed: ${player.money}"
    ))

    return results.failed == 0


def test_card_get_out_of_jail() -> bool:
    """Test GET_OUT_OF_JAIL card action."""
    print_header("GET_OUT_OF_JAIL CARD TESTS")
    results = TestResults()

    game = create_test_game()
    player = game.current_player

    print_subheader("Receive Get Out of Jail Free card")
    old_jail_cards = player.jail_cards
    
    card = Card(
        CardType.CHANCE,
        "Get Out of Jail Free.",
        CardAction.GET_OUT_OF_JAIL,
        keep=True
    )
    
    player.jail_cards += 1
    
    results.add(assert_test(
        player.jail_cards == old_jail_cards + 1,
        f"Player now has {player.jail_cards} jail card(s)",
        f"Jail cards incorrect: {player.jail_cards}"
    ))

    print_subheader("Card is kept (not discarded)")
    results.add(assert_test(
        card.keep == True,
        "Card is marked as keepable",
        "Card should be keepable"
    ))

    print_subheader("Multiple jail cards can be held")
    player.jail_cards += 1
    
    results.add(assert_test(
        player.jail_cards == old_jail_cards + 2,
        f"Player can hold multiple jail cards: {player.jail_cards}",
        f"Jail cards incorrect: {player.jail_cards}"
    ))

    return results.failed == 0


def test_card_collect_from_players() -> bool:
    """Test COLLECT_FROM_PLAYERS card action."""
    print_header("COLLECT_FROM_PLAYERS CARD TESTS")
    results = TestResults()

    game = create_test_game()
    current = game.current_player
    other_id = [pid for pid in game.player_order if pid != current.id][0]
    other = game.players[other_id]

    print_subheader("Birthday - collect $10 from each player")
    current_old = current.money
    other_old = other.money
    
    card = Card(
        CardType.COMMUNITY_CHEST,
        "It is your birthday. Collect $10 from every player.",
        CardAction.COLLECT_FROM_PLAYERS,
        value=10
    )
    
    # Simulate the collection
    total = 0
    for p in game.active_players:
        if p.id != current.id:
            amount = min(card.value, p.money)
            p.remove_money(amount)
            total += amount
    current.add_money(total)
    
    results.add(assert_test(
        other.money == other_old - 10,
        f"Other player paid $10: ${other.money}",
        f"Other player money incorrect: ${other.money}"
    ))
    
    results.add(assert_test(
        current.money == current_old + 10,
        f"Current player received $10: ${current.money}",
        f"Current player money incorrect: ${current.money}"
    ))

    print_subheader("Collect from player with insufficient funds")
    other.money = 5  # Less than $10
    current_old = current.money
    
    total = 0
    for p in game.active_players:
        if p.id != current.id:
            amount = min(card.value, p.money)
            p.remove_money(amount)
            total += amount
    current.add_money(total)
    
    results.add(assert_test(
        other.money == 0,
        f"Other player paid all they had: ${other.money}",
        f"Other player money incorrect: ${other.money}"
    ))
    
    results.add(assert_test(
        current.money == current_old + 5,
        f"Current player only received $5: ${current.money}",
        f"Current player money incorrect: ${current.money}"
    ))

    return results.failed == 0


def test_card_pay_to_players() -> bool:
    """Test PAY_TO_PLAYERS card action."""
    print_header("PAY_TO_PLAYERS CARD TESTS")
    results = TestResults()

    game = create_test_game()
    current = game.current_player
    other_id = [pid for pid in game.player_order if pid != current.id][0]
    other = game.players[other_id]

    print_subheader("Chairman of the Board - pay $50 to each player")
    current.money = 500
    current_old = current.money
    other_old = other.money
    
    card = Card(
        CardType.CHANCE,
        "You have been elected Chairman of the Board. Pay each player $50.",
        CardAction.PAY_TO_PLAYERS,
        value=50
    )
    
    # Calculate total owed
    other_players = [p for p in game.active_players if p.id != current.id]
    total_owed = card.value * len(other_players)
    
    if current.can_afford(total_owed):
        current.remove_money(total_owed)
        for p in other_players:
            p.add_money(card.value)
    
    results.add(assert_test(
        current.money == current_old - 50,
        f"Current player paid $50: ${current.money}",
        f"Current player money incorrect: ${current.money}"
    ))
    
    results.add(assert_test(
        other.money == other_old + 50,
        f"Other player received $50: ${other.money}",
        f"Other player money incorrect: ${other.money}"
    ))

    print_subheader("Cannot afford to pay all players")
    current.money = 30  # Less than $50
    
    can_pay = current.can_afford(50)
    
    results.add(assert_test(
        not can_pay,
        "Current player correctly cannot afford payment",
        "Player should not be able to afford"
    ))

    return results.failed == 0


def test_card_repairs() -> bool:
    """Test REPAIRS card action."""
    print_header("REPAIRS CARD TESTS")
    results = TestResults()

    game = create_test_game()
    player = game.current_player
    
    # Give player properties with houses
    prop1 = game.board.get_property(1)  # Mediterranean
    prop3 = game.board.get_property(3)  # Baltic
    prop1.owner_id = player.id
    prop3.owner_id = player.id
    player.add_property(1)
    player.add_property(3)

    print_subheader("Repairs with houses")
    prop1.houses = 3
    prop3.houses = 2
    player.money = 1000
    
    card = Card(
        CardType.CHANCE,
        "Make general repairs on all your property. For each house pay $25. For each hotel pay $100.",
        CardAction.REPAIRS,
        per_house=25,
        per_hotel=100
    )
    
    # Calculate repair cost
    total_cost = 0
    for pos in player.properties:
        prop = game.board.get_property(pos)
        if prop:
            total_cost += prop.houses * card.per_house
            if prop.has_hotel:
                total_cost += card.per_hotel
    
    expected_cost = (3 + 2) * 25  # 5 houses * $25 = $125
    
    results.add(assert_test(
        total_cost == expected_cost,
        f"Repair cost calculated correctly: ${total_cost}",
        f"Repair cost incorrect: ${total_cost} (expected ${expected_cost})"
    ))
    
    player.remove_money(total_cost)
    
    results.add(assert_test(
        player.money == 1000 - expected_cost,
        f"Player paid repairs: ${player.money}",
        f"Player money incorrect: ${player.money}"
    ))

    print_subheader("Repairs with hotels")
    prop1.houses = 0
    prop1.has_hotel = True
    prop3.houses = 4
    prop3.has_hotel = False
    player.money = 1000
    
    total_cost = 0
    for pos in player.properties:
        prop = game.board.get_property(pos)
        if prop:
            total_cost += prop.houses * card.per_house
            if prop.has_hotel:
                total_cost += card.per_hotel
    
    # 1 hotel ($100) + 4 houses ($100) = $200
    expected_cost = 100 + (4 * 25)
    
    results.add(assert_test(
        total_cost == expected_cost,
        f"Repair cost with hotel calculated correctly: ${total_cost}",
        f"Repair cost incorrect: ${total_cost} (expected ${expected_cost})"
    ))

    print_subheader("Street repairs (Community Chest - different rates)")
    card2 = Card(
        CardType.COMMUNITY_CHEST,
        "You are assessed for street repair. $40 per house. $115 per hotel.",
        CardAction.REPAIRS,
        per_house=40,
        per_hotel=115
    )
    
    total_cost = 0
    for pos in player.properties:
        prop = game.board.get_property(pos)
        if prop:
            total_cost += prop.houses * card2.per_house
            if prop.has_hotel:
                total_cost += card2.per_hotel
    
    # 1 hotel ($115) + 4 houses ($160) = $275
    expected_cost = 115 + (4 * 40)
    
    results.add(assert_test(
        total_cost == expected_cost,
        f"Street repair cost calculated correctly: ${total_cost}",
        f"Street repair cost incorrect: ${total_cost} (expected ${expected_cost})"
    ))

    print_subheader("No properties - no repair cost")
    player2_id = [pid for pid in game.player_order if pid != player.id][0]
    player2 = game.players[player2_id]
    player2.properties.clear()
    
    total_cost = 0
    for pos in player2.properties:
        prop = game.board.get_property(pos)
        if prop:
            total_cost += prop.houses * card.per_house
            if prop.has_hotel:
                total_cost += card.per_hotel
    
    results.add(assert_test(
        total_cost == 0,
        "Player with no properties pays $0 repairs",
        f"Repair cost should be $0: ${total_cost}"
    ))

    return results.failed == 0


def test_all_chance_cards_defined() -> bool:
    """Test that all Chance cards are properly defined."""
    print_header("CHANCE CARD DEFINITIONS")
    results = TestResults()

    print_subheader("Chance card count")
    results.add(assert_test(
        len(CHANCE_CARDS) == 16,
        f"16 Chance cards defined",
        f"Wrong count: {len(CHANCE_CARDS)}"
    ))

    print_subheader("All Chance cards have required attributes")
    all_valid = True
    for card in CHANCE_CARDS:
        if not (card.card_type == CardType.CHANCE and 
                card.text and 
                card.action):
            all_valid = False
            print_info(f"Invalid card: {card.text[:30]}...")
    
    results.add(assert_test(
        all_valid,
        "All Chance cards have required attributes",
        "Some Chance cards have missing attributes"
    ))

    return results.failed == 0


def test_all_community_chest_cards_defined() -> bool:
    """Test that all Community Chest cards are properly defined."""
    print_header("COMMUNITY CHEST CARD DEFINITIONS")
    results = TestResults()

    print_subheader("Community Chest card count")
    results.add(assert_test(
        len(COMMUNITY_CHEST_CARDS) == 16,
        f"16 Community Chest cards defined",
        f"Wrong count: {len(COMMUNITY_CHEST_CARDS)}"
    ))

    print_subheader("All Community Chest cards have required attributes")
    all_valid = True
    for card in COMMUNITY_CHEST_CARDS:
        if not (card.card_type == CardType.COMMUNITY_CHEST and 
                card.text and 
                card.action):
            all_valid = False
            print_info(f"Invalid card: {card.text[:30]}...")
    
    results.add(assert_test(
        all_valid,
        "All Community Chest cards have required attributes",
        "Some Community Chest cards have missing attributes"
    ))

    return results.failed == 0


def run_all_tests() -> bool:
    """Run all card tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              CARD ACTION TEST SUITE                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.RESET)

    all_results = TestResults()

    tests = [
        ("Collect Money", test_card_collect_money),
        ("Pay Money", test_card_pay_money),
        ("Move To Position", test_card_move_to_position),
        ("Nearest Utility", test_card_nearest_utility),
        ("Nearest Railroad", test_card_nearest_railroad),
        ("Move Back", test_card_move_back),
        ("Go To Jail", test_card_go_to_jail),
        ("Get Out of Jail", test_card_get_out_of_jail),
        ("Collect From Players", test_card_collect_from_players),
        ("Pay To Players", test_card_pay_to_players),
        ("Repairs", test_card_repairs),
        ("Chance Cards Defined", test_all_chance_cards_defined),
        ("Community Chest Cards Defined", test_all_community_chest_cards_defined),
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
