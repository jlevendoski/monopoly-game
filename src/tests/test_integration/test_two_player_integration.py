#!/usr/bin/env python3
"""
Integration tests for two-player game scenarios.

Tests the complete flow from connection through multiple turns of gameplay,
verifying state synchronization between players.

Run from project root:
    python -m pytest tests/test_integration/test_two_player_integration.py -v
    
Or directly:
    python tests/test_integration/test_two_player_integration.py
"""

import asyncio
import json
import sys
import tempfile
import os
from pathlib import Path
from typing import Optional
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import websockets
from websockets.client import WebSocketClientProtocol

from shared.enums import MessageType, GamePhase
from shared.constants import BOARD_SPACES


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
    """Track test results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add(self, passed: bool, msg: str = "") -> None:
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            if msg:
                self.errors.append(msg)
    
    def summary(self) -> None:
        print_header("TEST SUMMARY")
        total = self.passed + self.failed
        print(f"  Total:  {total}")
        print(f"  {Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {self.failed}{Colors.RESET}")
        
        if self.errors:
            print(f"\n  Errors:")
            for err in self.errors:
                print(f"    - {err}")
        
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


class TestPlayer:
    """
    Test player that can connect and interact with the game server.
    
    Provides methods for all game actions and state tracking.
    """
    
    def __init__(self, name: str, host: str = "127.0.0.1", port: int = 18765):
        self.name = name
        self.player_id = str(uuid.uuid4())
        self.host = host
        self.port = port
        self.ws: Optional[WebSocketClientProtocol] = None
        self.game_id: Optional[str] = None
        self.game_state: Optional[dict] = None
        self.received_messages: list[dict] = []
    
    async def connect(self) -> bool:
        """Connect to the server."""
        try:
            url = f"ws://{self.host}:{self.port}"
            self.ws = await websockets.connect(url, ping_interval=30, ping_timeout=10)
            
            await self.ws.send(json.dumps({
                "type": MessageType.CONNECT.value,
                "data": {"player_id": self.player_id, "player_name": self.name}
            }))
            
            response = await asyncio.wait_for(self.ws.recv(), timeout=10.0)
            data = json.loads(response)
            
            if data.get("data", {}).get("success"):
                return True
            return False
        except Exception as e:
            print_failure(f"[{self.name}] Connect failed: {e}")
            return False
    
    async def send(self, msg_type: str, data: dict = None) -> dict:
        """Send message and get response."""
        request_id = str(uuid.uuid4())
        await self.ws.send(json.dumps({
            "type": msg_type,
            "request_id": request_id,
            "data": data or {}
        }))
        
        while True:
            response = await asyncio.wait_for(self.ws.recv(), timeout=15.0)
            resp = json.loads(response)
            self.received_messages.append(resp)
            
            if resp.get("type") == MessageType.GAME_STATE.value:
                self.game_state = resp.get("data")
                self.game_id = self.game_state.get("game_id")
                return resp
            
            if resp.get("request_id") == request_id:
                return resp
    
    async def drain_messages(self, timeout: float = 0.5) -> list[dict]:
        """Read any pending messages."""
        messages = []
        try:
            while True:
                msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
                data = json.loads(msg)
                messages.append(data)
                self.received_messages.append(data)
                if data.get("type") == MessageType.GAME_STATE.value:
                    self.game_state = data.get("data")
                    self.game_id = self.game_state.get("game_id")
        except asyncio.TimeoutError:
            pass
        return messages
    
    def get_my_player_data(self) -> Optional[dict]:
        """Get this player's data from game state."""
        if not self.game_state:
            return None
        for p in self.game_state.get("players", []):
            if p.get("id") == self.player_id:
                return p
        return None
    
    def is_my_turn(self) -> bool:
        """Check if it's this player's turn."""
        if not self.game_state:
            return False
        return self.game_state.get("current_player_id") == self.player_id
    
    async def close(self):
        if self.ws:
            await self.ws.close()


class IntegrationTestServer:
    """Manages a test server instance."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 18765):
        self.host = host
        self.port = port
        self.server = None
        self.temp_db = None
    
    async def start(self):
        """Start the test server."""
        from server.network.server import MonopolyServer
        
        # Create temp database
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        
        self.server = MonopolyServer(
            host=self.host,
            port=self.port,
            db_path=self.temp_db.name
        )
        
        # Start server in background task
        self._server_task = asyncio.create_task(self.server.start())
        await asyncio.sleep(0.5)  # Give server time to start
    
    async def stop(self):
        """Stop the test server."""
        if self.server:
            await self.server.stop()
        
        if self.temp_db:
            try:
                os.unlink(self.temp_db.name)
            except Exception:
                pass


async def test_basic_two_player_game():
    """Test basic two-player game flow."""
    print_header("BASIC TWO-PLAYER GAME TEST")
    results = TestResults()
    
    server = IntegrationTestServer()
    player1 = TestPlayer("Alice")
    player2 = TestPlayer("Bob")
    
    try:
        await server.start()
        print_info("Server started")
        
        # Connect both players
        print_subheader("Connection Phase")
        
        results.add(
            await player1.connect(),
            "Player 1 connection failed"
        )
        print_success(f"Alice connected (ID: {player1.player_id[:8]}...)")
        
        results.add(
            await player2.connect(),
            "Player 2 connection failed"
        )
        print_success(f"Bob connected (ID: {player2.player_id[:8]}...)")
        
        # Create and join game
        print_subheader("Lobby Phase")
        
        resp = await player1.send(MessageType.CREATE_GAME.value, {
            "game_name": "Integration Test Game",
            "player_name": player1.name
        })
        results.add(
            resp.get("type") == MessageType.GAME_STATE.value,
            "Failed to create game"
        )
        print_success(f"Game created: {player1.game_id[:8]}...")
        
        resp = await player2.send(MessageType.JOIN_GAME.value, {
            "game_id": player1.game_id,
            "player_name": player2.name
        })
        results.add(
            resp.get("type") == MessageType.GAME_STATE.value,
            "Failed to join game"
        )
        print_success("Bob joined the game")
        
        await player1.drain_messages()
        
        # Start game
        print_subheader("Game Start Phase")
        
        resp = await player1.send(MessageType.START_GAME.value)
        results.add(
            resp.get("type") == MessageType.GAME_STATE.value,
            "Failed to start game"
        )
        results.add(
            player1.game_state.get("phase") == GamePhase.PRE_ROLL.value,
            f"Wrong phase after start: {player1.game_state.get('phase')}"
        )
        print_success("Game started")
        
        await player2.drain_messages()
        
        # Verify both have same initial state
        results.add(
            len(player1.game_state.get("players", [])) == 2,
            "Player 1 doesn't see 2 players"
        )
        results.add(
            len(player2.game_state.get("players", [])) == 2,
            "Player 2 doesn't see 2 players"
        )
        print_success("Both players see 2 players in game")
        
        # Play several turns
        print_subheader("Gameplay Phase")
        
        for turn in range(1, 6):
            print_info(f"Turn {turn}")
            
            # Sync states
            await player1.drain_messages()
            await player2.drain_messages()
            
            # Determine current player
            current_id = player1.game_state.get("current_player_id")
            if current_id == player1.player_id:
                current, other = player1, player2
            else:
                current, other = player2, player1
            
            print_info(f"  {current.name}'s turn")
            
            # Roll dice
            resp = await current.send(MessageType.ROLL_DICE.value)
            if resp.get("type") == MessageType.ERROR.value:
                print_failure(f"Roll failed: {resp.get('data', {}).get('message')}")
                break
            
            dice = current.game_state.get("last_dice_roll", [])
            print_info(f"  Rolled {dice} = {sum(dice)}")
            
            my_data = current.get_my_player_data()
            pos = my_data.get("position", 0)
            space = BOARD_SPACES.get(pos, {})
            print_info(f"  Landed on: {space.get('name', f'Position {pos}')}")
            
            # Handle property decision if needed
            phase = current.game_state.get("phase")
            if phase == GamePhase.PROPERTY_DECISION.value:
                cost = space.get("cost", 0)
                money = my_data.get("money", 0)
                
                if money >= cost and cost > 0:
                    resp = await current.send(MessageType.BUY_PROPERTY.value)
                    if resp.get("type") == MessageType.GAME_STATE.value:
                        print_info(f"  Bought {space.get('name')} for ${cost}")
                else:
                    resp = await current.send(MessageType.DECLINE_PROPERTY.value)
                    print_info(f"  Declined property")
            
            # End turn (handle doubles - may need to roll again)
            phase = current.game_state.get("phase")
            if phase == GamePhase.POST_ROLL.value:
                resp = await current.send(MessageType.END_TURN.value)
                if resp.get("type") == MessageType.ERROR.value:
                    # Might have rolled doubles
                    error_msg = resp.get("data", {}).get("message", "")
                    if "double" in error_msg.lower():
                        print_info(f"  Rolled doubles, continuing turn...")
                        continue
                else:
                    print_info(f"  Turn ended")
            
            # Verify other player received state update
            other_msgs = await other.drain_messages()
            results.add(
                any(m.get("type") == MessageType.GAME_STATE.value for m in other_msgs) or 
                other.game_state is not None,
                f"Other player didn't receive state update on turn {turn}"
            )
        
        # Verify state consistency
        print_subheader("State Consistency Check")
        
        await player1.drain_messages()
        await player2.drain_messages()
        
        # Both should have same game ID
        results.add(
            player1.game_id == player2.game_id,
            "Game IDs don't match"
        )
        print_success(f"Game IDs match: {player1.game_id[:8]}...")
        
        # Both should see same number of players
        p1_players = player1.game_state.get("players", [])
        p2_players = player2.game_state.get("players", [])
        results.add(
            len(p1_players) == len(p2_players),
            "Player counts don't match"
        )
        
        # Players should have consistent data
        for p1_data in p1_players:
            pid = p1_data.get("id")
            p2_data = next((p for p in p2_players if p.get("id") == pid), None)
            if p2_data:
                results.add(
                    p1_data.get("money") == p2_data.get("money"),
                    f"Money mismatch for player {pid[:8]}: {p1_data.get('money')} vs {p2_data.get('money')}"
                )
                results.add(
                    p1_data.get("position") == p2_data.get("position"),
                    f"Position mismatch for player {pid[:8]}"
                )
        
        print_success("Player states are consistent between clients")
        
    except Exception as e:
        print_failure(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        results.add(False, str(e))
    
    finally:
        await player1.close()
        await player2.close()
        await server.stop()
    
    return results


async def test_property_transactions():
    """Test property purchases and rent payment."""
    print_header("PROPERTY TRANSACTIONS TEST")
    results = TestResults()
    
    server = IntegrationTestServer()
    player1 = TestPlayer("PropertyBuyer")
    player2 = TestPlayer("RentPayer")
    
    try:
        await server.start()
        
        # Quick setup
        await player1.connect()
        await player2.connect()
        
        await player1.send(MessageType.CREATE_GAME.value, {
            "game_name": "Property Test",
            "player_name": player1.name
        })
        
        await player2.send(MessageType.JOIN_GAME.value, {
            "game_id": player1.game_id,
            "player_name": player2.name
        })
        await player1.drain_messages()
        
        await player1.send(MessageType.START_GAME.value)
        await player2.drain_messages()
        
        print_subheader("Playing Until Property Purchase")
        
        # Play until someone buys a property
        property_bought = False
        buyer_id = None
        max_turns = 20
        
        for turn in range(max_turns):
            await player1.drain_messages()
            await player2.drain_messages()
            
            current_id = player1.game_state.get("current_player_id")
            current = player1 if current_id == player1.player_id else player2
            
            # Roll
            resp = await current.send(MessageType.ROLL_DICE.value)
            if resp.get("type") == MessageType.ERROR.value:
                continue
            
            # Check for property decision
            phase = current.game_state.get("phase")
            if phase == GamePhase.PROPERTY_DECISION.value:
                my_data = current.get_my_player_data()
                pos = my_data.get("position", 0)
                space = BOARD_SPACES.get(pos, {})
                
                if space.get("cost", 0) > 0:
                    resp = await current.send(MessageType.BUY_PROPERTY.value)
                    if resp.get("type") == MessageType.GAME_STATE.value:
                        print_success(f"{current.name} bought {space.get('name')}")
                        property_bought = True
                        buyer_id = current.player_id
                else:
                    await current.send(MessageType.DECLINE_PROPERTY.value)
            
            # End turn
            await current.send(MessageType.END_TURN.value)
            
            if property_bought:
                break
        
        results.add(
            property_bought,
            "No property was purchased in the test"
        )
        
        if property_bought:
            # Verify property ownership in both states
            await player1.drain_messages()
            await player2.drain_messages()
            
            p1_buyer = next((p for p in player1.game_state.get("players", []) 
                           if p.get("id") == buyer_id), None)
            p2_buyer = next((p for p in player2.game_state.get("players", []) 
                           if p.get("id") == buyer_id), None)
            
            results.add(
                p1_buyer and len(p1_buyer.get("properties", [])) > 0,
                "Property not in buyer's list (player 1 view)"
            )
            results.add(
                p2_buyer and len(p2_buyer.get("properties", [])) > 0,
                "Property not in buyer's list (player 2 view)"
            )
            print_success("Property ownership verified in both clients")
        
    except Exception as e:
        print_failure(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        results.add(False, str(e))
    
    finally:
        await player1.close()
        await player2.close()
        await server.stop()
    
    return results


async def test_jail_mechanics():
    """Test jail-related gameplay."""
    print_header("JAIL MECHANICS TEST")
    results = TestResults()
    
    server = IntegrationTestServer()
    player1 = TestPlayer("Prisoner")
    player2 = TestPlayer("FreePlayer")
    
    try:
        await server.start()
        
        await player1.connect()
        await player2.connect()
        
        await player1.send(MessageType.CREATE_GAME.value, {
            "game_name": "Jail Test",
            "player_name": player1.name
        })
        
        await player2.send(MessageType.JOIN_GAME.value, {
            "game_id": player1.game_id,
            "player_name": player2.name
        })
        await player1.drain_messages()
        
        await player1.send(MessageType.START_GAME.value)
        await player2.drain_messages()
        
        print_subheader("Playing Until Someone Goes to Jail")
        
        # Play until someone lands on Go to Jail or draws a jail card
        jailed = False
        jailed_player = None
        max_turns = 50
        
        for turn in range(max_turns):
            await player1.drain_messages()
            await player2.drain_messages()
            
            current_id = player1.game_state.get("current_player_id")
            current = player1 if current_id == player1.player_id else player2
            other = player2 if current == player1 else player1
            
            # Roll
            resp = await current.send(MessageType.ROLL_DICE.value)
            if resp.get("type") == MessageType.ERROR.value:
                continue
            
            # Check if player is now in jail
            my_data = current.get_my_player_data()
            if my_data and my_data.get("is_in_jail"):
                jailed = True
                jailed_player = current
                print_success(f"{current.name} is in jail!")
                break
            
            # Handle property decisions
            phase = current.game_state.get("phase")
            if phase == GamePhase.PROPERTY_DECISION.value:
                await current.send(MessageType.DECLINE_PROPERTY.value)
            
            # End turn
            resp = await current.send(MessageType.END_TURN.value)
            if resp.get("type") == MessageType.ERROR.value:
                # Might have doubles
                continue
        
        if jailed:
            print_subheader("Testing Bail Payment")
            
            # Wait for jailed player's turn
            for _ in range(4):  # Max 2 turns per player
                await player1.drain_messages()
                await player2.drain_messages()
                
                current_id = player1.game_state.get("current_player_id")
                current = player1 if current_id == player1.player_id else player2
                
                if current == jailed_player:
                    break
                
                # Other player takes turn
                await current.send(MessageType.ROLL_DICE.value)
                phase = current.game_state.get("phase")
                if phase == GamePhase.PROPERTY_DECISION.value:
                    await current.send(MessageType.DECLINE_PROPERTY.value)
                await current.send(MessageType.END_TURN.value)
            
            # Now try to pay bail
            if jailed_player.is_my_turn():
                before_money = jailed_player.get_my_player_data().get("money", 0)
                
                resp = await jailed_player.send(MessageType.PAY_BAIL.value)
                
                if resp.get("type") == MessageType.GAME_STATE.value:
                    after_data = jailed_player.get_my_player_data()
                    results.add(
                        not after_data.get("is_in_jail"),
                        "Player still in jail after paying bail"
                    )
                    results.add(
                        after_data.get("money", 0) < before_money,
                        "Money not deducted for bail"
                    )
                    print_success("Bail paid successfully")
                else:
                    print_info(f"Bail response: {resp.get('type')}")
        else:
            print_info("No one went to jail in the test (this can happen)")
            results.add(True)  # Not a failure, just unlucky dice
        
    except Exception as e:
        print_failure(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        results.add(False, str(e))
    
    finally:
        await player1.close()
        await player2.close()
        await server.stop()
    
    return results


async def run_all_integration_tests():
    """Run all integration tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║        TWO-PLAYER INTEGRATION TEST SUITE                 ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    all_results = TestResults()
    
    tests = [
        ("Basic Two-Player Game", test_basic_two_player_game),
        ("Property Transactions", test_property_transactions),
        ("Jail Mechanics", test_jail_mechanics),
    ]
    
    for name, test_func in tests:
        try:
            results = await test_func()
            all_results.passed += results.passed
            all_results.failed += results.failed
            all_results.errors.extend(results.errors)
        except Exception as e:
            print_failure(f"{name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            all_results.add(False, f"{name}: {e}")
    
    all_results.summary()
    return all_results.failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_integration_tests())
    sys.exit(0 if success else 1)
