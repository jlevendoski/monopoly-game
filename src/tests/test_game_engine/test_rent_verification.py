#!/usr/bin/env python3
"""
Rent Calculation Verification Test

This is an impartial, standalone verification of all rent calculation scenarios.
It tests the actual game engine implementation against expected Monopoly rules.

Run: python tests/test_game_engine/test_rent_verification.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.game_engine import Game


def create_game():
    """Create a fresh game with two players."""
    game = Game(name='Rent Verification')
    game.add_player('Alice')
    game.add_player('Bob')
    game.start_game()
    
    alice = game.current_player
    bob_id = [pid for pid in game.player_order if pid != alice.id][0]
    bob = game.players[bob_id]
    
    return game, alice, bob


def run_verification():
    """Run all rent verification tests."""
    print()
    print("=" * 70)
    print("           RENT CALCULATION VERIFICATION REPORT")
    print("=" * 70)
    print()
    
    all_passed = True
    test_count = 0
    pass_count = 0
    
    def verify(description, actual, expected):
        nonlocal all_passed, test_count, pass_count
        test_count += 1
        
        if actual == expected:
            print(f"  ✓ {description}")
            print(f"      Result: ${actual} (correct)")
            pass_count += 1
            return True
        else:
            print(f"  ✗ {description}")
            print(f"      Expected: ${expected}, Got: ${actual}")
            all_passed = False
            return False
    
    # ========================================
    # SECTION 1: Basic Property Rent
    # ========================================
    print("-" * 70)
    print("SECTION 1: Basic Property Rent")
    print("-" * 70)
    
    game, alice, bob = create_game()
    
    # 1.1 Unowned property
    rent = game.board.calculate_rent(1, landing_player_id=alice.id)
    verify("Unowned property rent", rent, 0)
    
    # 1.2 Own property
    med = game.board.get_property(1)
    med.owner_id = alice.id
    alice.add_property(1)
    rent = game.board.calculate_rent(1, landing_player_id=alice.id)
    verify("Landing on own property", rent, 0)
    
    # 1.3 Other player's property (no monopoly)
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    verify("Mediterranean base rent (no monopoly)", rent, 2)
    
    # 1.4 Mortgaged property
    med.is_mortgaged = True
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    verify("Mortgaged property rent", rent, 0)
    
    print()
    
    # ========================================
    # SECTION 2: Monopoly Rent (No Houses)
    # ========================================
    print("-" * 70)
    print("SECTION 2: Monopoly Rent (Double Rent, No Houses)")
    print("-" * 70)
    
    game, alice, bob = create_game()
    
    # Brown monopoly: Mediterranean ($2 base) and Baltic ($4 base)
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    verify("Mediterranean with monopoly (2×$2)", rent, 4)
    
    rent = game.board.calculate_rent(3, landing_player_id=bob.id)
    verify("Baltic with monopoly (2×$4)", rent, 8)
    
    # Light Blue monopoly
    game.board.reset()
    for pos in [6, 8, 9]:
        prop = game.board.get_property(pos)
        prop.owner_id = alice.id
        alice.add_property(pos)
    
    rent = game.board.calculate_rent(6, landing_player_id=bob.id)
    verify("Oriental with monopoly (2×$6)", rent, 12)
    
    print()
    
    # ========================================
    # SECTION 3: Rent with Houses
    # ========================================
    print("-" * 70)
    print("SECTION 3: Rent with Houses (Mediterranean Avenue)")
    print("-" * 70)
    
    game, alice, bob = create_game()
    
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    
    # Mediterranean rents: [2, 10, 30, 90, 160, 250]
    test_cases = [
        (1, 10, "1 house"),
        (2, 30, "2 houses"),
        (3, 90, "3 houses"),
        (4, 160, "4 houses"),
    ]
    
    for houses, expected, desc in test_cases:
        med.houses = houses
        rent = game.board.calculate_rent(1, landing_player_id=bob.id)
        verify(f"Mediterranean with {desc}", rent, expected)
    
    # Hotel
    med.houses = 0
    med.has_hotel = True
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    verify("Mediterranean with hotel", rent, 250)
    
    print()
    
    # ========================================
    # SECTION 4: Railroad Rent Scaling
    # ========================================
    print("-" * 70)
    print("SECTION 4: Railroad Rent Scaling")
    print("-" * 70)
    
    game, alice, bob = create_game()
    
    railroads = [5, 15, 25, 35]
    expected_rents = [25, 50, 100, 200]
    
    for i, pos in enumerate(railroads):
        rr = game.board.get_property(pos)
        rr.owner_id = alice.id
        alice.add_property(pos)
        
        rent = game.board.calculate_rent(pos, landing_player_id=bob.id)
        verify(f"Railroad rent with {i+1} owned", rent, expected_rents[i])
    
    print()
    
    # ========================================
    # SECTION 5: Utility Rent
    # ========================================
    print("-" * 70)
    print("SECTION 5: Utility Rent (Dice Multiplier)")
    print("-" * 70)
    
    game, alice, bob = create_game()
    
    electric = game.board.get_property(12)
    electric.owner_id = alice.id
    alice.add_property(12)
    
    # 1 utility: 4× dice
    for dice in [2, 7, 12]:
        rent = game.board.calculate_rent(12, dice_roll=dice, landing_player_id=bob.id)
        verify(f"1 utility, dice={dice} (4×{dice})", rent, 4 * dice)
    
    # 2 utilities: 10× dice
    water = game.board.get_property(28)
    water.owner_id = alice.id
    alice.add_property(28)
    
    for dice in [2, 7, 12]:
        rent = game.board.calculate_rent(12, dice_roll=dice, landing_player_id=bob.id)
        verify(f"2 utilities, dice={dice} (10×{dice})", rent, 10 * dice)
    
    print()
    
    # ========================================
    # SECTION 6: Mortgaged Properties in Groups
    # ========================================
    print("-" * 70)
    print("SECTION 6: Mortgaged Properties (Monopoly/Group Ownership)")
    print("-" * 70)
    
    game, alice, bob = create_game()
    
    # Key rule: Ownership counts for multipliers even if mortgaged
    # But landing on mortgaged = $0 rent
    
    # Utility test
    electric = game.board.get_property(12)
    water = game.board.get_property(28)
    electric.owner_id = alice.id
    water.owner_id = alice.id
    alice.add_property(12)
    alice.add_property(28)
    
    electric.is_mortgaged = True
    
    rent = game.board.calculate_rent(12, dice_roll=7, landing_player_id=bob.id)
    verify("Landing on mortgaged utility", rent, 0)
    
    rent = game.board.calculate_rent(28, dice_roll=7, landing_player_id=bob.id)
    verify("Unmortgaged utility (both owned, 10×7)", rent, 70)
    
    # Railroad test
    game.board.reset()
    for pos in [5, 15, 25, 35]:
        rr = game.board.get_property(pos)
        rr.owner_id = alice.id
        alice.add_property(pos)
    
    game.board.get_property(5).is_mortgaged = True
    
    rent = game.board.calculate_rent(5, landing_player_id=bob.id)
    verify("Landing on mortgaged railroad", rent, 0)
    
    rent = game.board.calculate_rent(15, landing_player_id=bob.id)
    verify("Unmortgaged railroad (all 4 owned)", rent, 200)
    
    # Property monopoly test
    game.board.reset()
    med = game.board.get_property(1)
    baltic = game.board.get_property(3)
    med.owner_id = alice.id
    baltic.owner_id = alice.id
    alice.add_property(1)
    alice.add_property(3)
    
    med.is_mortgaged = True
    
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    verify("Landing on mortgaged property in monopoly", rent, 0)
    
    rent = game.board.calculate_rent(3, landing_player_id=bob.id)
    verify("Unmortgaged property (still has monopoly, 2×$4)", rent, 8)
    
    print()
    
    # ========================================
    # SECTION 7: Expensive Properties
    # ========================================
    print("-" * 70)
    print("SECTION 7: Expensive Properties (Boardwalk)")
    print("-" * 70)
    
    game, alice, bob = create_game()
    
    park = game.board.get_property(37)
    boardwalk = game.board.get_property(39)
    park.owner_id = alice.id
    boardwalk.owner_id = alice.id
    alice.add_property(37)
    alice.add_property(39)
    
    rent = game.board.calculate_rent(39, landing_player_id=bob.id)
    verify("Boardwalk base with monopoly (2×$50)", rent, 100)
    
    boardwalk.houses = 4
    park.houses = 4
    rent = game.board.calculate_rent(39, landing_player_id=bob.id)
    verify("Boardwalk with 4 houses", rent, 1700)
    
    boardwalk.houses = 0
    boardwalk.has_hotel = True
    rent = game.board.calculate_rent(39, landing_player_id=bob.id)
    verify("Boardwalk with hotel", rent, 2000)
    
    print()
    
    # ========================================
    # SUMMARY
    # ========================================
    print("=" * 70)
    print("                         VERIFICATION SUMMARY")
    print("=" * 70)
    print()
    print(f"  Total Tests:  {test_count}")
    print(f"  Passed:       {pass_count}")
    print(f"  Failed:       {test_count - pass_count}")
    print()
    
    if all_passed:
        print("  ╔════════════════════════════════════════════════════════════════╗")
        print("  ║     ALL RENT CALCULATIONS VERIFIED CORRECTLY ✓                ║")
        print("  ╚════════════════════════════════════════════════════════════════╝")
        return True
    else:
        print("  ╔════════════════════════════════════════════════════════════════╗")
        print("  ║     SOME RENT CALCULATIONS FAILED ✗                           ║")
        print("  ╚════════════════════════════════════════════════════════════════╝")
        return False


if __name__ == "__main__":
    success = run_verification()
    print()
    sys.exit(0 if success else 1)
