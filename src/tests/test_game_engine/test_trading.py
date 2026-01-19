"""
Comprehensive tests for trading validation.

Tests all trading scenarios including:
- Property trades
- Money trades
- Jail card trades
- Invalid trades (buildings, ownership, funds)
- Combined trades

Note: These tests validate the RuleEngine.validate_trade() method.
The actual trade execution would need to be implemented in Game class.

Run from project root: python -m pytest tests/test_game_engine/test_trading.py -v
Or run directly: python tests/test_game_engine/test_trading.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.game_engine import Game, Player, Board, RuleEngine, ActionResult
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
    game = Game(name="Trade Test Game")
    game.add_player("Alice")
    game.add_player("Bob")
    game.start_game()
    return game


def test_simple_property_trade() -> bool:
    """Test a simple property-for-property trade."""
    print_header("SIMPLE PROPERTY TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Give each player a property
    med = game.board.get_property(1)  # Mediterranean
    baltic = game.board.get_property(3)  # Baltic
    
    med.owner_id = alice.id
    alice.add_property(1)
    
    baltic.owner_id = bob.id
    bob.add_property(3)

    print_subheader("Valid property-for-property trade")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[1],
        requested_properties=[3],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        validation.valid,
        "Property-for-property trade is valid",
        f"Trade should be valid: {validation.message}"
    ))

    print_subheader("Trade non-existent property")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[99],  # Invalid position
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.NOT_OWNER,
        "Cannot trade non-existent property",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def test_property_for_money_trade() -> bool:
    """Test trading property for money."""
    print_header("PROPERTY FOR MONEY TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Alice owns Mediterranean
    med = game.board.get_property(1)
    med.owner_id = alice.id
    alice.add_property(1)

    print_subheader("Valid property-for-money trade")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=100,
        offered_properties=[1],
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        validation.valid,
        "Property-for-money trade is valid",
        f"Trade should be valid: {validation.message}"
    ))

    print_subheader("Money-for-property trade")
    validation = game.rules.validate_trade(
        from_player=bob,
        to_player=alice,
        offered_money=150,
        requested_money=0,
        offered_properties=[],
        requested_properties=[1],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        validation.valid,
        "Money-for-property trade is valid",
        f"Trade should be valid: {validation.message}"
    ))

    print_subheader("Requested money exceeds other player's funds")
    bob.money = 50  # Bob only has $50
    
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=100,
        offered_properties=[1],
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.INSUFFICIENT_FUNDS,
        "Cannot request more money than other player has",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def test_money_trade() -> bool:
    """Test pure money trades (gifts essentially)."""
    print_header("MONEY TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    print_subheader("Valid money offer (gift)")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=100,
        requested_money=0,
        offered_properties=[],
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        validation.valid,
        "Money gift is valid",
        f"Trade should be valid: {validation.message}"
    ))

    print_subheader("Offered money exceeds player's funds")
    alice.money = 50
    
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=100,
        requested_money=0,
        offered_properties=[],
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.INSUFFICIENT_FUNDS,
        "Cannot offer more money than you have",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def test_jail_card_trade() -> bool:
    """Test trading Get Out of Jail Free cards."""
    print_header("JAIL CARD TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    alice.jail_cards = 1
    bob.jail_cards = 2

    print_subheader("Valid jail card trade")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[],
        requested_properties=[],
        offered_jail_cards=1,
        requested_jail_cards=1
    )
    
    results.add(assert_test(
        validation.valid,
        "Jail card trade is valid",
        f"Trade should be valid: {validation.message}"
    ))

    print_subheader("Jail card for money")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=50,
        offered_properties=[],
        requested_properties=[],
        offered_jail_cards=1,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        validation.valid,
        "Jail card for money is valid",
        f"Trade should be valid: {validation.message}"
    ))

    print_subheader("Cannot trade more jail cards than owned")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[],
        requested_properties=[],
        offered_jail_cards=2,  # Alice only has 1
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.INVALID_TRADE,
        "Cannot trade more jail cards than owned",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Cannot request more jail cards than other player has")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[],
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=3  # Bob only has 2
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.INVALID_TRADE,
        "Cannot request more jail cards than other player has",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def test_cannot_trade_property_with_buildings() -> bool:
    """Test that properties with buildings cannot be traded."""
    print_header("PROPERTY WITH BUILDINGS TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Give Alice monopoly with houses
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    
    med.houses = 2

    print_subheader("Cannot trade property with houses")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[1],  # Has houses
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.HAS_BUILDINGS,
        "Cannot trade property with houses",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Cannot trade property with hotel")
    med.houses = 0
    med.has_hotel = True
    
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[1],  # Has hotel
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.HAS_BUILDINGS,
        "Cannot trade property with hotel",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Can trade other property in monopoly without buildings")
    baltic.houses = 0
    baltic.has_hotel = False
    
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[3],  # Baltic has no buildings
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        validation.valid,
        "Can trade property without buildings",
        f"Trade should be valid: {validation.message}"
    ))

    return results.failed == 0


def test_cannot_trade_unowned_property() -> bool:
    """Test that players cannot trade properties they don't own."""
    print_header("UNOWNED PROPERTY TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Mediterranean is unowned
    med = game.board.get_property(1)
    med.owner_id = None

    print_subheader("Cannot offer property you don't own")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[1],  # Alice doesn't own this
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.NOT_OWNER,
        "Cannot offer property you don't own",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Cannot request property other player doesn't own")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=100,
        requested_money=0,
        offered_properties=[],
        requested_properties=[1],  # Bob doesn't own this
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.NOT_OWNER,
        "Cannot request property other player doesn't own",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Cannot offer property owned by other player")
    med.owner_id = bob.id
    bob.add_property(1)
    
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[1],  # Owned by Bob, not Alice
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.NOT_OWNER,
        "Cannot offer property owned by other player",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def test_empty_trade_invalid() -> bool:
    """Test that trades must involve at least one item."""
    print_header("EMPTY TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    print_subheader("Empty trade is invalid")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[],
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.INVALID_TRADE,
        "Empty trade is invalid",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def test_complex_trade() -> bool:
    """Test complex trades involving multiple items."""
    print_header("COMPLEX TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Set up properties
    med = game.board.get_property(1)
    oriental = game.board.get_property(6)
    reading = game.board.get_property(5)
    
    med.owner_id = alice.id
    oriental.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(6)
    
    reading.owner_id = bob.id
    bob.add_property(5)

    alice.jail_cards = 1
    bob.jail_cards = 0

    print_subheader("Multiple properties for property + money + jail card")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=200,
        offered_properties=[1, 6],
        requested_properties=[5],
        offered_jail_cards=1,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        validation.valid,
        "Complex trade is valid",
        f"Trade should be valid: {validation.message}"
    ))

    print_subheader("Complex trade with one invalid property fails entire trade")
    med.houses = 1  # Add house to one property
    
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=200,
        offered_properties=[1, 6],  # 1 has houses now
        requested_properties=[5],
        offered_jail_cards=1,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.HAS_BUILDINGS,
        "Trade with one problematic property fails entirely",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def test_trade_mortgaged_property() -> bool:
    """Test that mortgaged properties can be traded."""
    print_header("MORTGAGED PROPERTY TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Alice owns mortgaged Mediterranean
    med = game.board.get_property(1)
    med.owner_id = alice.id
    med.is_mortgaged = True
    alice.add_property(1)

    print_subheader("Can trade mortgaged property")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=0,
        offered_properties=[1],  # Mortgaged
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    # Note: The current implementation allows trading mortgaged properties
    # This is actually correct per Monopoly rules - you can trade mortgaged
    # properties, the new owner just has to pay 10% interest if they unmortgage
    results.add(assert_test(
        validation.valid,
        "Mortgaged property can be traded",
        f"Trade should be valid: {validation.message}"
    ))

    return results.failed == 0


def test_trade_railroad() -> bool:
    """Test trading railroads."""
    print_header("RAILROAD TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Alice owns Reading Railroad
    reading = game.board.get_property(5)
    reading.owner_id = alice.id
    alice.add_property(5)

    print_subheader("Can trade railroad")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=150,
        offered_properties=[5],  # Reading Railroad
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        validation.valid,
        "Railroad trade is valid",
        f"Trade should be valid: {validation.message}"
    ))

    return results.failed == 0


def test_trade_utility() -> bool:
    """Test trading utilities."""
    print_header("UTILITY TRADE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Alice owns Electric Company
    electric = game.board.get_property(12)
    electric.owner_id = alice.id
    alice.add_property(12)

    print_subheader("Can trade utility")
    validation = game.rules.validate_trade(
        from_player=alice,
        to_player=bob,
        offered_money=0,
        requested_money=100,
        offered_properties=[12],  # Electric Company
        requested_properties=[],
        offered_jail_cards=0,
        requested_jail_cards=0
    )
    
    results.add(assert_test(
        validation.valid,
        "Utility trade is valid",
        f"Trade should be valid: {validation.message}"
    ))

    return results.failed == 0


def run_all_tests() -> bool:
    """Run all trading tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              TRADING VALIDATION TEST SUITE               ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.RESET)

    all_results = TestResults()

    tests = [
        ("Simple Property Trade", test_simple_property_trade),
        ("Property for Money", test_property_for_money_trade),
        ("Money Trade", test_money_trade),
        ("Jail Card Trade", test_jail_card_trade),
        ("Property with Buildings", test_cannot_trade_property_with_buildings),
        ("Unowned Property", test_cannot_trade_unowned_property),
        ("Empty Trade", test_empty_trade_invalid),
        ("Complex Trade", test_complex_trade),
        ("Mortgaged Property", test_trade_mortgaged_property),
        ("Railroad Trade", test_trade_railroad),
        ("Utility Trade", test_trade_utility),
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
