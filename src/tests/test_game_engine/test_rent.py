"""
Comprehensive tests for rent calculation edge cases.

Tests all rent scenarios including:
- Mortgaged properties (no rent)
- Utility rent with dice multipliers
- Railroad rent scaling
- Monopoly double rent
- Landing on own property

Run from project root: python -m pytest tests/test_game_engine/test_rent.py -v
Or run directly: python tests/test_game_engine/test_rent.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.game_engine import Game, Player, Board
from shared.enums import GamePhase, SpaceType
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
    game = Game(name="Rent Test Game")
    game.add_player("Alice")
    game.add_player("Bob")
    game.start_game()
    return game


def test_rent_on_mortgaged_property() -> bool:
    """Test that mortgaged properties charge no rent."""
    print_header("MORTGAGED PROPERTY RENT TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Alice owns Mediterranean Avenue
    prop = game.board.get_property(1)  # Mediterranean
    prop.owner_id = alice.id
    alice.add_property(1)

    print_subheader("Rent before mortgage")
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 2,  # Base rent for Mediterranean
        f"Base rent is $2 before mortgage",
        f"Rent is ${rent} (expected $2)"
    ))

    print_subheader("Rent after mortgage")
    prop.is_mortgaged = True
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 0,
        f"Rent is $0 on mortgaged property",
        f"Rent is ${rent} (expected $0)"
    ))

    print_subheader("Rent restored after unmortgage")
    prop.is_mortgaged = False
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 2,
        f"Rent restored to $2 after unmortgage",
        f"Rent is ${rent} (expected $2)"
    ))

    return results.failed == 0


def test_utility_rent_one_owned() -> bool:
    """Test utility rent when one utility is owned (4x dice)."""
    print_header("UTILITY RENT - ONE OWNED TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Alice owns Electric Company (position 12)
    prop = game.board.get_property(12)
    prop.owner_id = alice.id
    alice.add_property(12)

    print_subheader("Utility rent with dice roll 7")
    rent = game.board.calculate_rent(12, dice_roll=7, landing_player_id=bob.id)
    expected = 7 * 4  # 4x dice for one utility
    
    results.add(assert_test(
        rent == expected,
        f"Rent is ${rent} (7 × 4 = $28)",
        f"Rent is ${rent} (expected ${expected})"
    ))

    print_subheader("Utility rent with dice roll 12")
    rent = game.board.calculate_rent(12, dice_roll=12, landing_player_id=bob.id)
    expected = 12 * 4
    
    results.add(assert_test(
        rent == expected,
        f"Rent is ${rent} (12 × 4 = $48)",
        f"Rent is ${rent} (expected ${expected})"
    ))

    print_subheader("Utility rent with dice roll 2")
    rent = game.board.calculate_rent(12, dice_roll=2, landing_player_id=bob.id)
    expected = 2 * 4
    
    results.add(assert_test(
        rent == expected,
        f"Rent is ${rent} (2 × 4 = $8)",
        f"Rent is ${rent} (expected ${expected})"
    ))

    return results.failed == 0


def test_utility_rent_both_owned() -> bool:
    """Test utility rent when both utilities are owned (10x dice)."""
    print_header("UTILITY RENT - BOTH OWNED TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Alice owns both utilities
    electric = game.board.get_property(12)  # Electric Company
    water = game.board.get_property(28)  # Water Works
    electric.owner_id = alice.id
    water.owner_id = alice.id
    alice.add_property(12)
    alice.add_property(28)

    print_subheader("Both utilities rent with dice roll 7")
    rent = game.board.calculate_rent(12, dice_roll=7, landing_player_id=bob.id)
    expected = 7 * 10  # 10x dice for both utilities
    
    results.add(assert_test(
        rent == expected,
        f"Rent is ${rent} (7 × 10 = $70)",
        f"Rent is ${rent} (expected ${expected})"
    ))

    print_subheader("Both utilities rent with dice roll 12")
    rent = game.board.calculate_rent(28, dice_roll=12, landing_player_id=bob.id)
    expected = 12 * 10
    
    results.add(assert_test(
        rent == expected,
        f"Rent is ${rent} (12 × 10 = $120)",
        f"Rent is ${rent} (expected ${expected})"
    ))

    print_subheader("Landing on mortgaged utility = $0 rent")
    electric.is_mortgaged = True
    rent = game.board.calculate_rent(12, dice_roll=7, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 0,
        f"Mortgaged utility rent is $0",
        f"Rent is ${rent} (expected $0)"
    ))
    
    print_subheader("Other utility still uses both-owned multiplier")
    # Note: Per Monopoly rules, ownership count includes mortgaged properties
    # The landing property being unmortgaged still gets 10x multiplier
    rent = game.board.calculate_rent(28, dice_roll=7, landing_player_id=bob.id)
    expected = 7 * 10  # Still 10x because both are OWNED
    
    results.add(assert_test(
        rent == expected,
        f"Water Works rent with one mortgaged: ${rent} (still 10x)",
        f"Rent is ${rent} (expected ${expected})"
    ))

    return results.failed == 0


def test_railroad_rent_scaling() -> bool:
    """Test railroad rent scaling based on number owned."""
    print_header("RAILROAD RENT SCALING TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Railroads: 5, 15, 25, 35
    reading = game.board.get_property(5)
    penn = game.board.get_property(15)
    bo = game.board.get_property(25)
    short = game.board.get_property(35)

    print_subheader("One railroad: $25")
    reading.owner_id = alice.id
    alice.add_property(5)
    
    rent = game.board.calculate_rent(5, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 25,
        f"One railroad rent is $25",
        f"Rent is ${rent} (expected $25)"
    ))

    print_subheader("Two railroads: $50")
    penn.owner_id = alice.id
    alice.add_property(15)
    
    rent = game.board.calculate_rent(5, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 50,
        f"Two railroads rent is $50",
        f"Rent is ${rent} (expected $50)"
    ))

    print_subheader("Three railroads: $100")
    bo.owner_id = alice.id
    alice.add_property(25)
    
    rent = game.board.calculate_rent(5, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 100,
        f"Three railroads rent is $100",
        f"Rent is ${rent} (expected $100)"
    ))

    print_subheader("Four railroads: $200")
    short.owner_id = alice.id
    alice.add_property(35)
    
    rent = game.board.calculate_rent(5, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 200,
        f"Four railroads rent is $200",
        f"Rent is ${rent} (expected $200)"
    ))

    print_subheader("Landing on mortgaged railroad = $0 rent")
    reading.is_mortgaged = True
    
    # Rent for landing on mortgaged railroad is $0
    rent = game.board.calculate_rent(5, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 0,
        f"Mortgaged railroad rent is $0",
        f"Rent is ${rent} (expected $0)"
    ))
    
    print_subheader("Other railroads still use full ownership count")
    # Note: Per Monopoly rules, ownership count includes mortgaged properties
    # Landing on unmortgaged railroad still uses 4-railroad rent
    rent = game.board.calculate_rent(15, landing_player_id=bob.id)
    expected = 200  # Still counts all 4 railroads OWNED
    
    results.add(assert_test(
        rent == expected,
        f"Other railroads rent with one mortgaged: ${rent} (still 4-RR rate)",
        f"Rent is ${rent} (expected ${expected})"
    ))

    return results.failed == 0


def test_monopoly_double_rent() -> bool:
    """Test that monopoly doubles rent (without houses)."""
    print_header("MONOPOLY DOUBLE RENT TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Mediterranean and Baltic (Brown monopoly)
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)

    print_subheader("Single property (no monopoly): base rent")
    med.owner_id = alice.id
    alice.add_property(1)
    
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 2,
        f"Single property rent is $2",
        f"Rent is ${rent} (expected $2)"
    ))

    print_subheader("Monopoly (both owned): double rent")
    baltic.owner_id = alice.id
    alice.add_property(3)
    
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 4,
        f"Monopoly rent is $4 (doubled)",
        f"Rent is ${rent} (expected $4)"
    ))

    print_subheader("Baltic with monopoly")
    rent = game.board.calculate_rent(3, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 8,
        f"Baltic monopoly rent is $8 (doubled from $4)",
        f"Rent is ${rent} (expected $8)"
    ))

    print_subheader("Landing on mortgaged property in monopoly = $0")
    med.is_mortgaged = True
    
    # Landing on mortgaged: $0
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    results.add(assert_test(
        rent == 0,
        f"Mortgaged property rent is $0",
        f"Rent is ${rent}"
    ))
    
    print_subheader("Other property in monopoly still gets double rent")
    # Note: Monopoly is based on ownership, not mortgage status
    # Baltic still gets doubled rent because Alice OWNS both browns
    rent = game.board.calculate_rent(3, landing_player_id=bob.id)
    results.add(assert_test(
        rent == 8,
        f"Baltic in monopoly: $8 (still doubled)",
        f"Rent is ${rent} (expected $8)"
    ))

    return results.failed == 0


def test_rent_with_houses() -> bool:
    """Test rent calculations with houses."""
    print_header("RENT WITH HOUSES TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Give Alice monopoly on Brown
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)

    # Mediterranean rents: [2, 10, 30, 90, 160, 250]
    print_subheader("Mediterranean with 1 house: $10")
    med.houses = 1
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 10,
        f"1 house rent is $10",
        f"Rent is ${rent} (expected $10)"
    ))

    print_subheader("Mediterranean with 2 houses: $30")
    med.houses = 2
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 30,
        f"2 houses rent is $30",
        f"Rent is ${rent} (expected $30)"
    ))

    print_subheader("Mediterranean with 3 houses: $90")
    med.houses = 3
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 90,
        f"3 houses rent is $90",
        f"Rent is ${rent} (expected $90)"
    ))

    print_subheader("Mediterranean with 4 houses: $160")
    med.houses = 4
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 160,
        f"4 houses rent is $160",
        f"Rent is ${rent} (expected $160)"
    ))

    print_subheader("Mediterranean with hotel: $250")
    med.houses = 0
    med.has_hotel = True
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 250,
        f"Hotel rent is $250",
        f"Rent is ${rent} (expected $250)"
    ))

    return results.failed == 0


def test_landing_on_own_property() -> bool:
    """Test that landing on own property charges no rent."""
    print_header("LANDING ON OWN PROPERTY TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player

    # Alice owns Mediterranean
    prop = game.board.get_property(1)
    prop.owner_id = alice.id
    alice.add_property(1)

    print_subheader("Landing on own property")
    rent = game.board.calculate_rent(1, landing_player_id=alice.id)
    
    results.add(assert_test(
        rent == 0,
        f"No rent charged for own property",
        f"Rent is ${rent} (expected $0)"
    ))

    print_subheader("Own property with houses")
    prop.houses = 3
    rent = game.board.calculate_rent(1, landing_player_id=alice.id)
    
    results.add(assert_test(
        rent == 0,
        f"No rent even with houses",
        f"Rent is ${rent} (expected $0)"
    ))

    print_subheader("Own railroad")
    rr = game.board.get_property(5)
    rr.owner_id = alice.id
    alice.add_property(5)
    
    rent = game.board.calculate_rent(5, landing_player_id=alice.id)
    
    results.add(assert_test(
        rent == 0,
        f"No rent for own railroad",
        f"Rent is ${rent} (expected $0)"
    ))

    print_subheader("Own utility")
    util = game.board.get_property(12)
    util.owner_id = alice.id
    alice.add_property(12)
    
    rent = game.board.calculate_rent(12, dice_roll=10, landing_player_id=alice.id)
    
    results.add(assert_test(
        rent == 0,
        f"No rent for own utility",
        f"Rent is ${rent} (expected $0)"
    ))

    return results.failed == 0


def test_rent_on_unowned_property() -> bool:
    """Test that unowned properties have no rent."""
    print_header("UNOWNED PROPERTY TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player

    print_subheader("Unowned regular property")
    prop = game.board.get_property(1)
    # Make sure it's unowned
    prop.owner_id = None
    
    rent = game.board.calculate_rent(1, landing_player_id=alice.id)
    
    results.add(assert_test(
        rent == 0,
        f"Unowned property has no rent",
        f"Rent is ${rent} (expected $0)"
    ))

    print_subheader("Unowned railroad")
    rr = game.board.get_property(5)
    rr.owner_id = None
    
    rent = game.board.calculate_rent(5, landing_player_id=alice.id)
    
    results.add(assert_test(
        rent == 0,
        f"Unowned railroad has no rent",
        f"Rent is ${rent} (expected $0)"
    ))

    print_subheader("Unowned utility")
    util = game.board.get_property(12)
    util.owner_id = None
    
    rent = game.board.calculate_rent(12, dice_roll=10, landing_player_id=alice.id)
    
    results.add(assert_test(
        rent == 0,
        f"Unowned utility has no rent",
        f"Rent is ${rent} (expected $0)"
    ))

    return results.failed == 0


def test_expensive_property_rents() -> bool:
    """Test rent calculations for expensive properties."""
    print_header("EXPENSIVE PROPERTY RENT TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Boardwalk rents: [50, 200, 600, 1400, 1700, 2000]
    park = game.board.get_property(37)  # Park Place
    boardwalk = game.board.get_property(39)  # Boardwalk
    
    park.owner_id = alice.id
    boardwalk.owner_id = alice.id
    alice.add_property(37)
    alice.add_property(39)

    print_subheader("Boardwalk base rent (monopoly)")
    rent = game.board.calculate_rent(39, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 100,  # 50 * 2 for monopoly
        f"Boardwalk monopoly base rent is $100",
        f"Rent is ${rent} (expected $100)"
    ))

    print_subheader("Boardwalk with hotel")
    boardwalk.houses = 0
    boardwalk.has_hotel = True
    park.houses = 4  # Even building
    
    rent = game.board.calculate_rent(39, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 2000,
        f"Boardwalk hotel rent is $2000",
        f"Rent is ${rent} (expected $2000)"
    ))

    return results.failed == 0


def test_three_property_monopoly() -> bool:
    """Test rent for three-property color groups."""
    print_header("THREE-PROPERTY MONOPOLY RENT TESTS")
    results = TestResults()

    game = create_test_game()
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]

    # Light Blue: Oriental (6), Vermont (8), Connecticut (9)
    oriental = game.board.get_property(6)
    vermont = game.board.get_property(8)
    connecticut = game.board.get_property(9)

    print_subheader("Single property (no monopoly)")
    oriental.owner_id = alice.id
    alice.add_property(6)
    
    rent = game.board.calculate_rent(6, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 6,  # Base rent
        f"Single property rent is $6",
        f"Rent is ${rent} (expected $6)"
    ))

    print_subheader("Two of three (no monopoly)")
    vermont.owner_id = alice.id
    alice.add_property(8)
    
    rent = game.board.calculate_rent(6, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 6,  # Still base rent, no monopoly
        f"Two of three still $6 (no monopoly)",
        f"Rent is ${rent} (expected $6)"
    ))

    print_subheader("Full monopoly (all three)")
    connecticut.owner_id = alice.id
    alice.add_property(9)
    
    rent = game.board.calculate_rent(6, landing_player_id=bob.id)
    
    results.add(assert_test(
        rent == 12,  # Doubled
        f"Full monopoly rent is $12 (doubled)",
        f"Rent is ${rent} (expected $12)"
    ))

    return results.failed == 0


def run_all_tests() -> bool:
    """Run all rent tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            RENT CALCULATION TEST SUITE                   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.RESET)

    all_results = TestResults()

    tests = [
        ("Mortgaged Property", test_rent_on_mortgaged_property),
        ("Utility - One Owned", test_utility_rent_one_owned),
        ("Utility - Both Owned", test_utility_rent_both_owned),
        ("Railroad Scaling", test_railroad_rent_scaling),
        ("Monopoly Double Rent", test_monopoly_double_rent),
        ("Rent With Houses", test_rent_with_houses),
        ("Own Property", test_landing_on_own_property),
        ("Unowned Property", test_rent_on_unowned_property),
        ("Expensive Properties", test_expensive_property_rents),
        ("Three-Property Monopoly", test_three_property_monopoly),
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
