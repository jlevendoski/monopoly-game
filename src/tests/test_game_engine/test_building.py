"""
Comprehensive tests for building mechanics edge cases.

Tests all building scenarios including:
- House shortage (32 house limit)
- Hotel shortage (12 hotel limit)
- Even building rule
- Building with mortgaged properties
- Selling buildings

Run from project root: python -m pytest tests/test_game_engine/test_building.py -v
Or run directly: python tests/test_game_engine/test_building.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.game_engine import Game, Player, Board, RuleEngine, ActionResult
from shared.enums import GamePhase
from shared.constants import TOTAL_HOUSES, TOTAL_HOTELS, MAX_HOUSES_PER_PROPERTY


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
    game = Game(name="Building Test Game")
    game.add_player("Alice")
    game.add_player("Bob")
    game.start_game()
    return game


def test_house_shortage() -> bool:
    """Test that house shortage is properly enforced."""
    print_header("HOUSE SHORTAGE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player

    print_subheader("Initial house count")
    results.add(assert_test(
        game.rules.houses_available == TOTAL_HOUSES,
        f"Game starts with {TOTAL_HOUSES} houses",
        f"House count wrong: {game.rules.houses_available}"
    ))

    print_subheader("Using houses decrements count")
    game.rules.use_house()
    game.rules.use_house()
    
    results.add(assert_test(
        game.rules.houses_available == TOTAL_HOUSES - 2,
        f"House count is now {game.rules.houses_available}",
        f"House count wrong: {game.rules.houses_available}"
    ))

    print_subheader("Cannot use house when none available")
    game.rules.houses_available = 0
    
    can_use = game.rules.use_house()
    
    results.add(assert_test(
        not can_use,
        "Cannot use house when none available",
        "Should not be able to use house"
    ))

    print_subheader("Validation fails when no houses available")
    # Give Alice monopoly on Brown
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    alice.money = 10000
    
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.NO_BUILDINGS_AVAILABLE,
        "Build validation fails: no houses available",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Returning house increases count")
    game.rules.houses_available = 5
    game.rules.return_house()
    
    results.add(assert_test(
        game.rules.houses_available == 6,
        f"House count increased to {game.rules.houses_available}",
        f"House count wrong: {game.rules.houses_available}"
    ))

    return results.failed == 0


def test_hotel_shortage() -> bool:
    """Test that hotel shortage is properly enforced."""
    print_header("HOTEL SHORTAGE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player

    print_subheader("Initial hotel count")
    results.add(assert_test(
        game.rules.hotels_available == TOTAL_HOTELS,
        f"Game starts with {TOTAL_HOTELS} hotels",
        f"Hotel count wrong: {game.rules.hotels_available}"
    ))

    print_subheader("Using hotel decrements count and returns houses")
    initial_houses = game.rules.houses_available
    game.rules.use_hotel()
    
    results.add(assert_test(
        game.rules.hotels_available == TOTAL_HOTELS - 1,
        f"Hotel count is now {game.rules.hotels_available}",
        f"Hotel count wrong: {game.rules.hotels_available}"
    ))
    
    results.add(assert_test(
        game.rules.houses_available == initial_houses + 4,
        f"Houses returned: {game.rules.houses_available}",
        f"Houses should be {initial_houses + 4}"
    ))

    print_subheader("Cannot use hotel when none available")
    game.rules.hotels_available = 0
    
    can_use = game.rules.use_hotel()
    
    results.add(assert_test(
        not can_use,
        "Cannot use hotel when none available",
        "Should not be able to use hotel"
    ))

    print_subheader("Validation fails when no hotels available")
    # Give Alice monopoly on Brown with 4 houses
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    med.houses = 4
    baltic.houses = 4
    alice.money = 10000
    game.rules.houses_available = 10  # Some houses available
    
    validation = game.rules.validate_build_hotel(alice, 1, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.NO_BUILDINGS_AVAILABLE,
        "Hotel validation fails: no hotels available",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def test_even_building_rule() -> bool:
    """Test that even building rule is enforced."""
    print_header("EVEN BUILDING RULE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    game.phase = GamePhase.POST_ROLL

    # Give Alice monopoly on Brown
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    alice.money = 10000

    print_subheader("Can build first house on property")
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        validation.valid,
        "Can build first house",
        f"Should be able to build: {validation.message}"
    ))

    print_subheader("Cannot build second house before building on other property")
    med.houses = 1
    
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.UNEVEN_BUILDING,
        "Cannot build unevenly",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Can build second house after evening out")
    baltic.houses = 1
    
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        validation.valid,
        "Can build after evening out",
        f"Should be able to build: {validation.message}"
    ))

    print_subheader("Can build on either property when even")
    validation = game.rules.validate_build_house(alice, 3, alice.id)
    
    results.add(assert_test(
        validation.valid,
        "Can build on either property when even",
        f"Should be able to build: {validation.message}"
    ))

    return results.failed == 0


def test_even_building_three_property_group() -> bool:
    """Test even building on three-property color groups."""
    print_header("THREE-PROPERTY EVEN BUILDING TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    game.phase = GamePhase.POST_ROLL

    # Give Alice Light Blue monopoly (3 properties)
    oriental = game.board.get_property(6)
    vermont = game.board.get_property(8)
    connecticut = game.board.get_property(9)
    
    oriental.owner_id = alice.id
    vermont.owner_id = alice.id
    connecticut.owner_id = alice.id
    alice.add_property(6)
    alice.add_property(8)
    alice.add_property(9)
    alice.money = 10000

    print_subheader("Build on all three before second house on any")
    oriental.houses = 1
    
    # Cannot build on Oriental again
    validation = game.rules.validate_build_house(alice, 6, alice.id)
    results.add(assert_test(
        not validation.valid,
        "Cannot build second on Oriental yet",
        f"Should fail: {validation.message}"
    ))
    
    # Can build on Vermont
    validation = game.rules.validate_build_house(alice, 8, alice.id)
    results.add(assert_test(
        validation.valid,
        "Can build first on Vermont",
        f"Should be able to build: {validation.message}"
    ))
    
    vermont.houses = 1
    
    # Can build on Connecticut
    validation = game.rules.validate_build_house(alice, 9, alice.id)
    results.add(assert_test(
        validation.valid,
        "Can build first on Connecticut",
        f"Should be able to build: {validation.message}"
    ))
    
    connecticut.houses = 1
    
    # Now can build second on any
    validation = game.rules.validate_build_house(alice, 6, alice.id)
    results.add(assert_test(
        validation.valid,
        "Now can build second on Oriental",
        f"Should be able to build: {validation.message}"
    ))

    return results.failed == 0


def test_cannot_build_with_mortgaged_property_in_group() -> bool:
    """Test that cannot build when any property in group is mortgaged."""
    print_header("MORTGAGED PROPERTY IN GROUP TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    game.phase = GamePhase.POST_ROLL

    # Give Alice monopoly on Brown
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    alice.money = 10000

    print_subheader("Can build when no properties mortgaged")
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        validation.valid,
        "Can build when no properties mortgaged",
        f"Should be able to build: {validation.message}"
    ))

    print_subheader("Cannot build when other property in group is mortgaged")
    baltic.is_mortgaged = True
    
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.PROPERTY_MORTGAGED,
        "Cannot build with mortgaged property in group",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Cannot build on the mortgaged property itself")
    validation = game.rules.validate_build_house(alice, 3, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.PROPERTY_MORTGAGED,
        "Cannot build on mortgaged property",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Can build after unmortgaging")
    baltic.is_mortgaged = False
    
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        validation.valid,
        "Can build after unmortgaging",
        f"Should be able to build: {validation.message}"
    ))

    return results.failed == 0


def test_hotel_requires_four_houses() -> bool:
    """Test that building a hotel requires 4 houses first."""
    print_header("HOTEL REQUIRES FOUR HOUSES TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    game.phase = GamePhase.POST_ROLL

    # Give Alice monopoly on Brown
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    alice.money = 10000

    print_subheader("Cannot build hotel with 0 houses")
    med.houses = 0
    baltic.houses = 0
    
    validation = game.rules.validate_build_hotel(alice, 1, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.UNEVEN_BUILDING,
        "Cannot build hotel with 0 houses",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Cannot build hotel with 3 houses")
    med.houses = 3
    baltic.houses = 3
    
    validation = game.rules.validate_build_hotel(alice, 1, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.UNEVEN_BUILDING,
        "Cannot build hotel with 3 houses",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Can build hotel with 4 houses")
    med.houses = 4
    baltic.houses = 4
    
    validation = game.rules.validate_build_hotel(alice, 1, alice.id)
    
    results.add(assert_test(
        validation.valid,
        "Can build hotel with 4 houses",
        f"Should be able to build: {validation.message}"
    ))

    return results.failed == 0


def test_even_selling_rule() -> bool:
    """Test that even selling rule is enforced."""
    print_header("EVEN SELLING RULE TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player

    # Give Alice monopoly on Brown with houses
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)

    print_subheader("Can sell house from property with most houses")
    med.houses = 3
    baltic.houses = 2
    
    validation = game.rules.validate_sell_house(alice, 1)
    
    results.add(assert_test(
        validation.valid,
        "Can sell from property with most houses",
        f"Should be able to sell: {validation.message}"
    ))

    print_subheader("Cannot sell from property with fewer houses")
    validation = game.rules.validate_sell_house(alice, 3)  # Baltic has fewer
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.UNEVEN_BUILDING,
        "Cannot sell unevenly",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Can sell when even")
    med.houses = 2
    baltic.houses = 2
    
    # Can sell from either
    validation = game.rules.validate_sell_house(alice, 1)
    results.add(assert_test(
        validation.valid,
        "Can sell from either when even (med)",
        f"Should be able to sell: {validation.message}"
    ))
    
    validation = game.rules.validate_sell_house(alice, 3)
    results.add(assert_test(
        validation.valid,
        "Can sell from either when even (baltic)",
        f"Should be able to sell: {validation.message}"
    ))

    return results.failed == 0


def test_cannot_build_on_railroad_or_utility() -> bool:
    """Test that cannot build on railroads or utilities."""
    print_header("CANNOT BUILD ON RAILROAD/UTILITY TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    game.phase = GamePhase.POST_ROLL

    # Give Alice a railroad
    reading = game.board.get_property(5)
    reading.owner_id = alice.id
    alice.add_property(5)
    alice.money = 10000

    print_subheader("Cannot build on railroad")
    validation = game.rules.validate_build_house(alice, 5, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.INVALID_PROPERTY,
        "Cannot build on railroad",
        f"Should fail: {validation.message}"
    ))

    # Give Alice a utility
    electric = game.board.get_property(12)
    electric.owner_id = alice.id
    alice.add_property(12)

    print_subheader("Cannot build on utility")
    validation = game.rules.validate_build_house(alice, 12, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.INVALID_PROPERTY,
        "Cannot build on utility",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def test_cannot_build_without_monopoly() -> bool:
    """Test that cannot build without owning full color group."""
    print_header("MONOPOLY REQUIRED TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]
    game.phase = GamePhase.POST_ROLL

    # Alice owns Mediterranean, Bob owns Baltic
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = bob.id
    alice.add_property(1)
    bob.add_property(3)
    alice.money = 10000

    print_subheader("Cannot build without monopoly")
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.NO_MONOPOLY,
        "Cannot build without monopoly",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Can build after completing monopoly")
    baltic.owner_id = alice.id
    alice.add_property(3)
    
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        validation.valid,
        "Can build with monopoly",
        f"Should be able to build: {validation.message}"
    ))

    return results.failed == 0


def test_max_development_level() -> bool:
    """Test that properties max out at hotel."""
    print_header("MAX DEVELOPMENT LEVEL TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    game.phase = GamePhase.POST_ROLL

    # Give Alice monopoly on Brown with hotel
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    alice.money = 10000

    print_subheader("Cannot build house on property with 4 houses")
    med.houses = 4
    baltic.houses = 4
    
    validation = game.rules.validate_build_house(alice, 1, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.MAX_DEVELOPMENT,
        "Cannot add 5th house",
        f"Should fail: {validation.message}"
    ))

    print_subheader("Cannot build hotel on property with hotel")
    med.houses = 0
    med.has_hotel = True
    baltic.houses = 0
    baltic.has_hotel = True
    
    validation = game.rules.validate_build_hotel(alice, 1, alice.id)
    
    results.add(assert_test(
        not validation.valid and validation.result == ActionResult.MAX_DEVELOPMENT,
        "Cannot add second hotel",
        f"Should fail: {validation.message}"
    ))

    return results.failed == 0


def run_all_tests() -> bool:
    """Run all building tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              BUILDING MECHANICS TEST SUITE               ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.RESET)

    all_results = TestResults()

    tests = [
        ("House Shortage", test_house_shortage),
        ("Hotel Shortage", test_hotel_shortage),
        ("Even Building Rule", test_even_building_rule),
        ("Three-Property Even Building", test_even_building_three_property_group),
        ("Mortgaged Property in Group", test_cannot_build_with_mortgaged_property_in_group),
        ("Hotel Requires Four Houses", test_hotel_requires_four_houses),
        ("Even Selling Rule", test_even_selling_rule),
        ("Cannot Build on Railroad/Utility", test_cannot_build_on_railroad_or_utility),
        ("Monopoly Required", test_cannot_build_without_monopoly),
        ("Max Development Level", test_max_development_level),
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
