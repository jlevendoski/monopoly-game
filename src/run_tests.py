#!/usr/bin/env python3
"""
Monopoly Test Suite - Single File

A comprehensive test suite for the Monopoly game engine.
Drop this file into src/ and run: python run_tests.py

Usage:
    python run_tests.py          # Run all tests
    python run_tests.py -q       # Quiet mode (summary only)
    python run_tests.py -v       # Verbose mode
    python run_tests.py --quick  # Quick tests only (skip slow integration)
"""

import sys
import os
import argparse
import asyncio
import tempfile
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple, Callable

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

# =============================================================================
# Test Utilities
# =============================================================================

class C:  # Colors
    G = "\033[92m"   # Green
    R = "\033[91m"   # Red
    Y = "\033[93m"   # Yellow
    B = "\033[94m"   # Blue
    C = "\033[96m"   # Cyan
    N = "\033[0m"    # Reset
    BOLD = "\033[1m"

# Disable colors if not TTY
if not (hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()):
    C.G = C.R = C.Y = C.B = C.C = C.N = C.BOLD = ""

@dataclass
class Results:
    passed: int = 0
    failed: int = 0
    
    def ok(self, cond: bool, msg: str = "") -> bool:
        if cond:
            self.passed += 1
        else:
            self.failed += 1
            if msg:
                print(f"  {C.R}✗ {msg}{C.N}")
        return cond
    
    def __add__(self, other: "Results") -> "Results":
        return Results(self.passed + other.passed, self.failed + other.failed)

def header(text: str) -> None:
    print(f"\n{C.BOLD}{C.B}{'='*60}\n {text}\n{'='*60}{C.N}")

def passed(msg: str) -> None:
    print(f"  {C.G}✓ {msg}{C.N}")

def failed(msg: str) -> None:
    print(f"  {C.R}✗ {msg}{C.N}")

def info(msg: str) -> None:
    print(f"  {C.Y}→ {msg}{C.N}")

def check(r: Results, cond: bool, ok_msg: str, fail_msg: str) -> None:
    if r.ok(cond, fail_msg):
        passed(ok_msg)

# =============================================================================
# Game Setup Helpers
# =============================================================================

def make_game(n_players: int = 2, start: bool = True):
    """Create a test game with players."""
    from server.game_engine import Game
    game = Game(name="Test")
    for name in ["Alice", "Bob", "Charlie", "Diana"][:n_players]:
        game.add_player(name)
    if start:
        game.start_game()
    return game

def give_monopoly(game, player, positions: List[int]) -> None:
    """Give player ownership of properties at positions."""
    for pos in positions:
        prop = game.board.get_property(pos)
        if prop:
            prop.owner_id = player.id
            if pos not in player.properties:
                player.add_property(pos)

def other_player(game, player):
    """Get a different player from the game."""
    for pid in game.player_order:
        if pid != player.id:
            return game.players[pid]
    return None

# =============================================================================
# Unit Tests - Game Engine Core
# =============================================================================

def test_dice() -> Results:
    """Test dice mechanics."""
    header("DICE TESTS")
    r = Results()
    from server.game_engine import Dice
    
    dice = Dice(seed=42)
    roll = dice.roll()
    check(r, 1 <= roll.die1 <= 6 and 1 <= roll.die2 <= 6, 
          f"Dice in range: {roll.die1}, {roll.die2}", "Dice out of range")
    check(r, roll.total == roll.die1 + roll.die2,
          f"Total correct: {roll.total}", "Total incorrect")
    
    # Test doubles detection
    dice = Dice(seed=12345)
    doubles = non_doubles = False
    for _ in range(100):
        roll = dice.roll()
        if roll.is_double:
            doubles = True
        else:
            non_doubles = True
        if doubles and non_doubles:
            break
    check(r, doubles, "Doubles can occur", "No doubles in 100 rolls")
    check(r, non_doubles, "Non-doubles can occur", "Only doubles in 100 rolls")
    return r

def test_player() -> Results:
    """Test player mechanics."""
    header("PLAYER TESTS")
    r = Results()
    from server.game_engine import Player
    from shared.enums import PlayerState
    from shared.constants import STARTING_MONEY, SALARY_AMOUNT, JAIL_POSITION
    
    p = Player(name="Test")
    check(r, p.money == STARTING_MONEY, f"Starting money: ${p.money}", "Wrong starting money")
    check(r, p.position == 0, "Starts at GO", f"Wrong start pos: {p.position}")
    
    # Money operations
    p.add_money(500)
    check(r, p.money == STARTING_MONEY + 500, "Add money works", "Add money failed")
    p.remove_money(200)
    check(r, p.money == STARTING_MONEY + 300, "Remove money works", "Remove money failed")
    check(r, p.can_afford(1000), "Can afford $1000", "Should afford $1000")
    check(r, not p.can_afford(10000), "Cannot afford $10000", "Should not afford $10000")
    
    # Movement
    p.position = 35
    old_money = p.money
    passed_go = p.move_forward(10)
    check(r, p.position == 5, f"Wraparound works: pos {p.position}", "Wraparound failed")
    check(r, passed_go and p.money == old_money + SALARY_AMOUNT, 
          f"GO salary collected", "GO salary not collected")
    
    # Jail
    p.send_to_jail()
    check(r, p.position == JAIL_POSITION and p.state == PlayerState.IN_JAIL,
          "Sent to jail", "Jail failed")
    p.release_from_jail()
    check(r, p.state == PlayerState.ACTIVE, "Released from jail", "Release failed")
    return r

def test_board() -> Results:
    """Test board and property mechanics."""
    header("BOARD TESTS")
    r = Results()
    from server.game_engine import Board
    
    board = Board()
    check(r, len(board.properties) == 28, f"28 properties: {len(board.properties)}", "Wrong property count")
    
    # Property lookup
    med = board.get_property(1)
    check(r, med and med.name == "Mediterranean Avenue", "Mediterranean at pos 1", "Wrong property")
    check(r, med.cost == 60, "Mediterranean costs $60", f"Wrong cost: ${med.cost}")
    
    # Ownership
    check(r, board.is_property_available(1), "Property available", "Should be available")
    med.owner_id = "p1"
    check(r, not board.is_property_available(1), "Property not available after purchase", "Should be taken")
    
    # Monopoly detection
    board.get_property(3).owner_id = "p1"  # Baltic
    check(r, board.player_has_monopoly("p1", "BROWN"), "Brown monopoly detected", "Monopoly not detected")
    check(r, not board.player_has_monopoly("p1", "LIGHT_BLUE"), "No light blue monopoly", "False monopoly")
    
    # Rent calculation
    rent = med.calculate_rent(has_monopoly=False)
    check(r, rent == 2, f"Base rent $2", f"Wrong rent: ${rent}")
    rent = med.calculate_rent(has_monopoly=True)
    check(r, rent == 4, f"Monopoly rent $4", f"Wrong monopoly rent: ${rent}")
    
    # Building
    med.build_house()
    check(r, med.houses == 1, "House built", "House not built")
    rent = med.calculate_rent()
    check(r, rent == 10, f"1-house rent $10", f"Wrong rent: ${rent}")
    
    # Mortgage
    board.reset()
    med = board.get_property(1)
    med.owner_id = "p1"
    val = med.mortgage()
    check(r, val == 30 and med.is_mortgaged, f"Mortgaged for ${val}", "Mortgage failed")
    check(r, med.calculate_rent() == 0, "Mortgaged = no rent", "Mortgaged rent should be 0")
    return r

def test_cards() -> Results:
    """Test card mechanics."""
    header("CARD TESTS")
    r = Results()
    from server.game_engine import CardManager
    from server.game_engine.cards import CHANCE_CARDS, COMMUNITY_CHEST_CARDS
    
    cards = CardManager()
    
    # Draw variety
    chance_texts = {cards.draw_chance().text for _ in range(20)}
    cc_texts = {cards.draw_community_chest().text for _ in range(20)}
    check(r, len(chance_texts) > 5, f"Chance variety: {len(chance_texts)} unique", "Low chance variety")
    check(r, len(cc_texts) > 5, f"CC variety: {len(cc_texts)} unique", "Low CC variety")
    
    # Card counts
    check(r, len(CHANCE_CARDS) == 16, "16 Chance cards", f"Wrong count: {len(CHANCE_CARDS)}")
    check(r, len(COMMUNITY_CHEST_CARDS) == 16, "16 CC cards", f"Wrong count: {len(COMMUNITY_CHEST_CARDS)}")
    
    # Reshuffle
    cards.reset()
    for _ in range(50):
        cards.draw_chance()
    check(r, True, "Deck reshuffles", "Reshuffle failed")
    return r

def test_game_flow() -> Results:
    """Test game flow and turn management."""
    header("GAME FLOW TESTS")
    r = Results()
    from shared.enums import GamePhase
    
    game = make_game(2, start=False)
    check(r, game.phase == GamePhase.WAITING, "Starts in WAITING", f"Wrong phase: {game.phase}")
    
    # Can't start with 1 player
    game2 = make_game(1, start=False)
    ok, msg = game2.start_game()
    check(r, not ok, f"Can't start with 1 player: {msg}", "Should need 2+ players")
    
    # Start game
    ok, msg = game.start_game()
    check(r, ok and game.phase == GamePhase.PRE_ROLL, "Game started", f"Start failed: {msg}")
    
    # Current player
    current = game.current_player
    check(r, current is not None, f"Current player: {current.name}", "No current player")
    
    # Roll dice
    ok, msg, roll = game.roll_dice(current.id)
    check(r, ok and roll is not None, f"Rolled {roll.die1}+{roll.die2}={roll.total}", f"Roll failed: {msg}")
    
    # Can't add player after start
    ok, msg, _ = game.add_player("Late")
    check(r, not ok, f"Can't add after start: {msg}", "Should block late join")
    
    # Wrong player can't roll
    other_id = [pid for pid in game.player_order if pid != current.id][0]
    ok, msg, _ = game.roll_dice(other_id)
    check(r, not ok, f"Wrong player blocked: {msg}", "Should block wrong player")
    return r

def test_property_actions() -> Results:
    """Test property purchase, building, mortgage."""
    header("PROPERTY ACTIONS TESTS")
    r = Results()
    from shared.enums import GamePhase
    
    # Buy property
    game = make_game(2)
    player = game.current_player
    player.position = 1
    game.phase = GamePhase.PROPERTY_DECISION
    old_money = player.money
    
    ok, msg = game.buy_property(player.id)
    check(r, ok, f"Bought property: {msg}", f"Buy failed: {msg}")
    check(r, player.money == old_money - 60, f"Money deducted: ${player.money}", "Money not deducted")
    check(r, 1 in player.properties, "Property in player's list", "Property not added")
    
    # Building requires monopoly
    game2 = make_game(2)
    p = game2.current_player
    prop = game2.board.get_property(1)
    prop.owner_id = p.id
    p.add_property(1)
    game2.phase = GamePhase.POST_ROLL
    
    ok, msg = game2.build_house(p.id, 1)
    check(r, not ok, f"No build without monopoly: {msg}", "Should require monopoly")
    
    # Build with monopoly
    give_monopoly(game2, p, [1, 3])
    ok, msg = game2.build_house(p.id, 1)
    check(r, ok, f"Built house: {msg}", f"Build failed: {msg}")
    
    # Even building
    ok, msg = game2.build_house(p.id, 1)
    check(r, not ok, f"Even building enforced: {msg}", "Should enforce even building")
    ok, msg = game2.build_house(p.id, 3)
    check(r, ok, f"Built on other: {msg}", f"Even build failed: {msg}")
    
    # Mortgage with buildings fails
    ok, msg = game2.mortgage_property(p.id, 1)
    check(r, not ok, f"Can't mortgage with buildings: {msg}", "Should block mortgage")
    return r

def test_jail() -> Results:
    """Test jail mechanics."""
    header("JAIL TESTS")
    r = Results()
    from shared.enums import PlayerState, GamePhase
    from shared.constants import JAIL_POSITION, JAIL_BAIL
    
    game = make_game(2)
    player = game.current_player
    
    # Send to jail
    player.send_to_jail()
    check(r, player.state == PlayerState.IN_JAIL, "Player in jail", f"Wrong state: {player.state}")
    check(r, player.position == JAIL_POSITION, f"At jail pos {player.position}", "Wrong position")
    
    # Pay bail
    game.phase = GamePhase.PRE_ROLL
    old_money = player.money
    ok, msg = game.pay_bail(player.id)
    check(r, ok, f"Paid bail: {msg}", f"Bail failed: {msg}")
    check(r, player.state == PlayerState.ACTIVE, "Released", f"Still jailed: {player.state}")
    check(r, player.money == old_money - JAIL_BAIL, f"Bail deducted: ${player.money}", "Bail not deducted")
    
    # Use jail card
    game2 = make_game(2)
    p2 = game2.current_player
    p2.send_to_jail()
    p2.jail_cards = 1
    game2.phase = GamePhase.PRE_ROLL
    
    ok, msg = game2.use_jail_card(p2.id)
    check(r, ok, "Used jail card", f"Card failed: {msg}")
    check(r, p2.state == PlayerState.ACTIVE, "Released by card", "Not released")
    check(r, p2.jail_cards == 0, "Card consumed", "Card not consumed")
    return r

def test_bankruptcy() -> Results:
    """Test bankruptcy mechanics."""
    header("BANKRUPTCY TESTS")
    r = Results()
    from shared.enums import PlayerState
    
    game = make_game(2)
    p1 = game.current_player
    p2 = other_player(game, p1)
    
    # Bankruptcy to bank
    p1.money = 0
    ok, msg = game.declare_bankruptcy(p1.id)
    check(r, ok, f"Bankruptcy declared: {msg}", f"Failed: {msg}")
    check(r, p1.state == PlayerState.BANKRUPT, "Marked bankrupt", f"Wrong state: {p1.state}")
    check(r, game.is_game_over, "Game over with 1 player", "Should be game over")
    
    # Bankruptcy to creditor
    game2 = make_game(2)
    alice = game2.current_player
    bob = other_player(game2, alice)
    
    give_monopoly(game2, alice, [1, 3])
    alice.money = 0
    bob_money = bob.money
    
    game2._handle_bankruptcy(alice, bob)
    check(r, 1 in bob.properties and 3 in bob.properties, 
          "Properties transferred", "Transfer failed")
    return r

def test_rent() -> Results:
    """Test rent calculations."""
    header("RENT TESTS")
    r = Results()
    
    game = make_game(2)
    alice = game.current_player
    bob = other_player(game, alice)
    
    # Base rent
    prop = game.board.get_property(1)  # Mediterranean
    prop.owner_id = alice.id
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    check(r, rent == 2, f"Base rent $2", f"Wrong: ${rent}")
    
    # Monopoly rent
    give_monopoly(game, alice, [1, 3])
    rent = game.board.calculate_rent(1, landing_player_id=bob.id)
    check(r, rent == 4, f"Monopoly rent $4", f"Wrong: ${rent}")
    
    # Railroad rent
    game.board.reset()
    rr = game.board.get_property(5)  # Reading RR
    rr.owner_id = alice.id
    rent = rr.calculate_rent(same_group_owned=1)
    check(r, rent == 25, f"1 RR rent $25", f"Wrong: ${rent}")
    
    for pos in [5, 15, 25, 35]:
        game.board.get_property(pos).owner_id = alice.id
    rent = game.board.get_property(5).calculate_rent(same_group_owned=4)
    check(r, rent == 200, f"4 RR rent $200", f"Wrong: ${rent}")
    
    # Utility rent
    game.board.reset()
    elec = game.board.get_property(12)
    elec.owner_id = alice.id
    rent = elec.calculate_rent(dice_roll=7, same_group_owned=1)
    check(r, rent == 28, f"1 util rent 4×7=$28", f"Wrong: ${rent}")
    
    game.board.get_property(28).owner_id = alice.id
    rent = elec.calculate_rent(dice_roll=7, same_group_owned=2)
    check(r, rent == 70, f"2 util rent 10×7=$70", f"Wrong: ${rent}")
    return r

def test_trading() -> Results:
    """Test trade validation."""
    header("TRADING TESTS")
    r = Results()
    from server.game_engine import ActionResult
    
    game = make_game(2)
    alice = game.current_player
    bob = other_player(game, alice)
    
    # Give properties
    game.board.get_property(1).owner_id = alice.id
    alice.add_property(1)
    game.board.get_property(3).owner_id = bob.id
    bob.add_property(3)
    
    # Valid trade
    v = game.rules.validate_trade(alice, bob, 0, 0, [1], [3], 0, 0)
    check(r, v.valid, "Property swap valid", f"Should be valid: {v.message}")
    
    # Can't trade unowned
    v = game.rules.validate_trade(alice, bob, 0, 0, [5], [], 0, 0)
    check(r, not v.valid and v.result == ActionResult.NOT_OWNER,
          "Can't trade unowned", "Should fail")
    
    # Can't trade with buildings
    game.board.get_property(1).houses = 1
    v = game.rules.validate_trade(alice, bob, 0, 0, [1], [], 0, 0)
    check(r, not v.valid and v.result == ActionResult.HAS_BUILDINGS,
          "Can't trade with buildings", "Should fail")
    
    # Empty trade invalid
    v = game.rules.validate_trade(alice, bob, 0, 0, [], [], 0, 0)
    check(r, not v.valid, "Empty trade invalid", "Should fail")
    return r

def test_serialization() -> Results:
    """Test save/load game state."""
    header("SERIALIZATION TESTS")
    r = Results()
    from server.game_engine import Game
    from server.game_engine.dice import DiceResult
    
    game = make_game(3)
    game.turn_number = 15
    game.last_dice_roll = DiceResult(die1=4, die2=5)
    
    alice = game.current_player
    alice.money = 800
    alice.position = 24
    give_monopoly(game, alice, [1, 3])
    game.board.get_property(1).houses = 2
    
    # Save
    data = game.to_dict()
    check(r, data["turn_number"] == 15, "Turn saved", "Turn not saved")
    check(r, data["last_dice_roll"] == [4, 5], "Dice saved", "Dice not saved")
    
    # Load
    loaded = Game.from_dict(data)
    check(r, loaded.id == game.id, "ID preserved", "ID changed")
    check(r, loaded.turn_number == 15, "Turn restored", "Turn wrong")
    
    loaded_alice = loaded.players.get(alice.id)
    check(r, loaded_alice and loaded_alice.money == 800, "Money restored", "Money wrong")
    check(r, loaded_alice and loaded_alice.position == 24, "Position restored", "Position wrong")
    
    loaded_prop = loaded.board.get_property(1)
    check(r, loaded_prop and loaded_prop.houses == 2, "Houses restored", "Houses wrong")
    return r

# =============================================================================
# Network Tests
# =============================================================================

def test_network() -> Results:
    """Test network layer (connection manager, game manager, message handler)."""
    header("NETWORK TESTS")
    r = Results()
    
    try:
        import websockets
    except ImportError:
        info("Skipping network tests (websockets not installed)")
        return r
    
    import json
    from unittest.mock import MagicMock
    
    class MockWS:
        def __init__(self, id):
            self.id = id
            self.sent = []
            self.closed = False
        async def send(self, data):
            self.sent.append(data)
        async def close(self):
            self.closed = True
        def __hash__(self):
            return hash(self.id)
        def __eq__(self, other):
            return isinstance(other, MockWS) and self.id == other.id
    
    async def run_tests():
        from server.network.connection_manager import ConnectionManager
        from server.network.game_manager import GameManager
        from server.persistence import init_database, GameRepository
        from shared.protocol import Message, GameSettings
        from shared.enums import MessageType
        
        # Connection manager tests
        cm = ConnectionManager()
        ws1, ws2 = MockWS("ws1"), MockWS("ws2")
        
        conn1 = await cm.connect(ws1, "p1", "Alice")
        conn2 = await cm.connect(ws2, "p2", "Bob")
        check(r, conn1.player_id == "p1", "Player connected", "Connect failed")
        check(r, cm.is_player_connected("p1"), "Player shows connected", "Connection status wrong")
        
        await cm.join_game("p1", "game1", is_host=True)
        await cm.join_game("p2", "game1")
        players = cm.get_players_in_game("game1")
        check(r, len(players) == 2, f"2 players in game", f"Wrong count: {len(players)}")
        
        host = cm.get_host("game1")
        check(r, host and host.player_id == "p1", "Host correct", "Wrong host")
        
        # Game manager tests
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            db = init_database(db_path)
            repo = GameRepository(db)
            gm = GameManager(repo)
            
            ok, msg, managed = gm.create_game("Test", "host1", "Alice", GameSettings())
            check(r, ok and managed, f"Game created", f"Create failed: {msg}")
            
            ok, msg, _ = gm.join_game(managed.game_id, "p2", "Bob")
            check(r, ok, "Player joined", f"Join failed: {msg}")
            
            ok, msg = gm.start_game(managed.game_id, "host1")
            check(r, ok, "Game started", f"Start failed: {msg}")
        finally:
            os.unlink(db_path)
        
        return r
    
    return asyncio.run(run_tests())

# =============================================================================
# Persistence Tests
# =============================================================================

def test_persistence() -> Results:
    """Test database persistence layer."""
    header("PERSISTENCE TESTS")
    r = Results()
    
    from server.persistence import init_database, GameRepository
    from server.persistence.models import GameRecord
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        db = init_database(db_path)
        repo = GameRepository(db)
        
        # Create game
        game = make_game(2)
        game.turn_number = 5
        
        record = GameRecord(id=game.id, name=game.name, status="active")
        saved = repo.create_game(record)
        check(r, saved is not None, "Game created", "Create failed")
        
        # Save game state
        snapshot_id = repo.save_game_state(game.id, game.to_dict(), game.turn_number)
        check(r, snapshot_id > 0, f"State saved (snapshot {snapshot_id})", "Save failed")
        
        # List games
        games = repo.list_games()
        check(r, len(games) >= 1, f"Listed {len(games)} game(s)", "List failed")
        
        # Load game state
        import json
        loaded = repo.get_latest_game_state(game.id)
        check(r, loaded is not None, "State loaded", "Load failed")
        state_data = json.loads(loaded.state_json) if loaded else {}
        check(r, state_data.get("turn_number") == 5, 
              "Turn preserved", "Turn wrong")
        
        # Delete
        ok = repo.delete_game(game.id)
        check(r, ok, "Game deleted", "Delete failed")
        check(r, repo.get_game(game.id) is None, "Deletion confirmed", "Still exists")
        
    finally:
        os.unlink(db_path)
    
    return r

# =============================================================================
# Integration Tests (requires websockets)
# =============================================================================

def test_integration() -> Results:
    """Test two-player game flow through the server."""
    header("INTEGRATION TESTS")
    r = Results()
    
    try:
        import websockets
    except ImportError:
        info("Skipping integration tests (websockets not installed)")
        return r
    
    import json
    import uuid
    
    async def run_test():
        from server.network.server import MonopolyServer
        from shared.enums import MessageType, GamePhase
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            server = MonopolyServer(host="127.0.0.1", port=19876, db_path=db_path)
            server_task = asyncio.create_task(server.start())
            await asyncio.sleep(0.5)
            
            # Connect two players
            ws1 = await websockets.connect("ws://127.0.0.1:19876")
            ws2 = await websockets.connect("ws://127.0.0.1:19876")
            
            p1_id, p2_id = str(uuid.uuid4()), str(uuid.uuid4())
            
            await ws1.send(json.dumps({"type": "CONNECT", "data": {"player_id": p1_id, "player_name": "Alice"}}))
            resp = json.loads(await ws1.recv())
            check(r, resp.get("data", {}).get("success"), "P1 connected", "P1 connect failed")
            
            await ws2.send(json.dumps({"type": "CONNECT", "data": {"player_id": p2_id, "player_name": "Bob"}}))
            resp = json.loads(await ws2.recv())
            check(r, resp.get("data", {}).get("success"), "P2 connected", "P2 connect failed")
            
            # Create and join game
            await ws1.send(json.dumps({"type": "CREATE_GAME", "data": {"game_name": "Test", "player_name": "Alice"}}))
            resp = json.loads(await ws1.recv())
            game_id = resp.get("data", {}).get("game_id")
            check(r, game_id, f"Game created: {game_id[:8]}...", "Create failed")
            
            await ws2.send(json.dumps({"type": "JOIN_GAME", "data": {"game_id": game_id, "player_name": "Bob"}}))
            resp = json.loads(await ws2.recv())
            check(r, resp.get("type") == "GAME_STATE", "P2 joined", "Join failed")
            
            # Drain notifications
            async def drain(ws, timeout=0.3):
                msgs = []
                while True:
                    try:
                        msgs.append(json.loads(await asyncio.wait_for(ws.recv(), timeout)))
                    except asyncio.TimeoutError:
                        break
                return msgs
            
            await drain(ws1)
            
            # Start game
            await ws1.send(json.dumps({"type": "START_GAME", "data": {}}))
            await asyncio.sleep(0.3)
            await drain(ws1)
            await drain(ws2)
            
            check(r, True, "Game started", "Start failed")
            
            await ws1.close()
            await ws2.close()
            await server.stop()
            
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
        
        return r
    
    return asyncio.run(run_test())

# =============================================================================
# Main Runner
# =============================================================================

def run_all(quick: bool = False, verbose: bool = True) -> Results:
    """Run all tests."""
    total = Results()
    
    # Unit tests (always run)
    tests = [
        test_dice,
        test_player,
        test_board,
        test_cards,
        test_game_flow,
        test_property_actions,
        test_jail,
        test_bankruptcy,
        test_rent,
        test_trading,
        test_serialization,
    ]
    
    for test in tests:
        try:
            if verbose:
                result = test()
            else:
                import io
                from contextlib import redirect_stdout
                with redirect_stdout(io.StringIO()):
                    result = test()
            total = total + result
        except Exception as e:
            failed(f"{test.__name__} raised: {e}")
            total.failed += 1
    
    # Network/persistence/integration (skip if quick mode)
    if not quick:
        for test in [test_network, test_persistence, test_integration]:
            try:
                if verbose:
                    result = test()
                else:
                    import io
                    from contextlib import redirect_stdout
                    with redirect_stdout(io.StringIO()):
                        result = test()
                total = total + result
            except Exception as e:
                failed(f"{test.__name__} raised: {e}")
                total.failed += 1
    
    return total

def main() -> int:
    parser = argparse.ArgumentParser(description="Monopoly Test Suite")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode (default)")
    parser.add_argument("--quick", action="store_true", help="Quick mode (unit tests only)")
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    print(f"\n{C.BOLD}{C.C}{'='*60}")
    print(f" MONOPOLY TEST SUITE")
    print(f"{'='*60}{C.N}")
    
    start = time.time()
    results = run_all(quick=args.quick, verbose=verbose)
    elapsed = time.time() - start
    
    print(f"\n{C.BOLD}{C.C}{'='*60}")
    print(f" RESULTS")
    print(f"{'='*60}{C.N}")
    print(f"\n  Total:  {results.passed + results.failed}")
    print(f"  {C.G}Passed: {results.passed}{C.N}")
    print(f"  {C.R}Failed: {results.failed}{C.N}")
    print(f"  Time:   {elapsed:.2f}s")
    
    if results.failed == 0:
        print(f"\n{C.G}{C.BOLD}{'='*60}")
        print(f" ALL TESTS PASSED ✓")
        print(f"{'='*60}{C.N}")
        return 0
    else:
        print(f"\n{C.R}{C.BOLD}{'='*60}")
        print(f" SOME TESTS FAILED ✗")
        print(f"{'='*60}{C.N}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
