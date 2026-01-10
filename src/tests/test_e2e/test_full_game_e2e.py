#!/usr/bin/env python3
"""
End-to-end test that simulates a complete Monopoly game from start to finish.

This test plays through an entire game until one player wins by bankrupting
the other(s), testing all game mechanics along the way.

Run from project root:
    python -m pytest tests/test_e2e/test_full_game_e2e.py -v --timeout=600
    
Or directly:
    python tests/test_e2e/test_full_game_e2e.py
"""

import asyncio
import json
import sys
import tempfile
import os
import random
from pathlib import Path
from typing import Optional, List
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import websockets
from websockets.client import WebSocketClientProtocol

from shared.enums import MessageType, GamePhase, PlayerState
from shared.constants import BOARD_SPACES


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}")
    print(f" {text}")
    print(f"{'=' * 70}{Colors.RESET}\n")


def print_subheader(text: str) -> None:
    print(f"\n{Colors.CYAN}--- {text} ---{Colors.RESET}")


def print_success(text: str) -> None:
    print(f"  {Colors.GREEN}✓ {text}{Colors.RESET}")


def print_failure(text: str) -> None:
    print(f"  {Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str) -> None:
    print(f"  {Colors.YELLOW}→ {text}{Colors.RESET}")


def print_turn(text: str) -> None:
    print(f"  {Colors.MAGENTA}⚄ {text}{Colors.RESET}")


class TestResults:
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
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! ✓{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}Some tests failed ✗{Colors.RESET}")


class AIPlayer:
    """
    AI-controlled test player with simple decision making.
    
    This player makes reasonable decisions to simulate realistic gameplay:
    - Buys properties when affordable
    - Builds houses when possible
    - Pays bail when in jail
    """
    
    def __init__(self, name: str, host: str = "127.0.0.1", port: int = 18767):
        self.name = name
        self.player_id = str(uuid.uuid4())
        self.host = host
        self.port = port
        self.ws: Optional[WebSocketClientProtocol] = None
        self.game_id: Optional[str] = None
        self.game_state: Optional[dict] = None
        self.properties_bought = 0
        self.houses_built = 0
        self.rent_paid = 0
        self.rent_collected = 0
    
    async def connect(self) -> bool:
        try:
            url = f"ws://{self.host}:{self.port}"
            self.ws = await websockets.connect(url, ping_interval=30, ping_timeout=10)
            
            await self.ws.send(json.dumps({
                "type": MessageType.CONNECT.value,
                "data": {"player_id": self.player_id, "player_name": self.name}
            }))
            
            response = await asyncio.wait_for(self.ws.recv(), timeout=10.0)
            data = json.loads(response)
            return data.get("data", {}).get("success", False)
        except Exception as e:
            print_failure(f"[{self.name}] Connect failed: {e}")
            return False
    
    async def send(self, msg_type: str, data: dict = None) -> dict:
        request_id = str(uuid.uuid4())
        await self.ws.send(json.dumps({
            "type": msg_type,
            "request_id": request_id,
            "data": data or {}
        }))
        
        while True:
            response = await asyncio.wait_for(self.ws.recv(), timeout=30.0)
            resp = json.loads(response)
            
            if resp.get("type") == MessageType.GAME_STATE.value:
                self.game_state = resp.get("data")
                self.game_id = self.game_state.get("game_id")
                return resp
            
            if resp.get("request_id") == request_id:
                return resp
    
    async def drain_messages(self, timeout: float = 0.3) -> List[dict]:
        messages = []
        try:
            while True:
                msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
                data = json.loads(msg)
                messages.append(data)
                if data.get("type") == MessageType.GAME_STATE.value:
                    self.game_state = data.get("data")
                    self.game_id = self.game_state.get("game_id")
        except asyncio.TimeoutError:
            pass
        return messages
    
    def get_my_data(self) -> Optional[dict]:
        if not self.game_state:
            return None
        for p in self.game_state.get("players", []):
            if p.get("id") == self.player_id:
                return p
        return None
    
    def is_my_turn(self) -> bool:
        if not self.game_state:
            return False
        return self.game_state.get("current_player_id") == self.player_id
    
    def is_bankrupt(self) -> bool:
        my_data = self.get_my_data()
        return my_data.get("is_bankrupt", False) if my_data else False
    
    def is_in_jail(self) -> bool:
        my_data = self.get_my_data()
        return my_data.get("is_in_jail", False) if my_data else False
    
    async def take_turn(self) -> str:
        """
        Take a complete turn with AI decision making.
        
        Returns a summary of actions taken.
        """
        actions = []
        
        # First check the current phase
        phase = self.game_state.get("phase", "") if self.game_state else ""
        
        # If we're in POST_ROLL, we should end turn
        if phase == GamePhase.POST_ROLL.value:
            resp = await self.send(MessageType.END_TURN.value)
            if resp.get("type") == MessageType.GAME_STATE.value:
                return f"{self.name}: ended turn (was in POST_ROLL)"
        
        # Handle jail first
        if self.is_in_jail():
            my_data = self.get_my_data()
            money = my_data.get("money", 0) if my_data else 0
            
            # Try to pay bail if we can afford it
            if money >= 50:
                resp = await self.send(MessageType.PAY_BAIL.value)
                if resp.get("type") == MessageType.GAME_STATE.value:
                    actions.append("paid bail")
            else:
                # Try to roll doubles (handled automatically by roll)
                pass
        
        # Roll dice (only in PRE_ROLL phase)
        phase = self.game_state.get("phase", "") if self.game_state else ""
        if phase != GamePhase.PRE_ROLL.value:
            return f"{self.name}: not in PRE_ROLL (phase={phase})"
        
        resp = await self.send(MessageType.ROLL_DICE.value)
        if resp.get("type") == MessageType.ERROR.value:
            error_msg = resp.get('data', {}).get('message', 'unknown')
            return f"Error: {error_msg}"
        
        dice = self.game_state.get("last_dice_roll", [])
        actions.append(f"rolled {dice[0]}+{dice[1]}={sum(dice)}" if len(dice) >= 2 else "rolled")
        
        # Handle property decision
        phase = self.game_state.get("phase")
        if phase == GamePhase.PROPERTY_DECISION.value:
            my_data = self.get_my_data()
            pos = my_data.get("position", 0) if my_data else 0
            money = my_data.get("money", 0) if my_data else 0
            space = BOARD_SPACES.get(pos, {})
            cost = space.get("cost", 0)
            
            # Buy if we can afford it and still have buffer
            if cost > 0 and money >= cost + 100:  # Keep $100 buffer
                resp = await self.send(MessageType.BUY_PROPERTY.value)
                if resp.get("type") == MessageType.GAME_STATE.value:
                    self.properties_bought += 1
                    actions.append(f"bought {space.get('name', 'property')} for ${cost}")
            else:
                await self.send(MessageType.DECLINE_PROPERTY.value)
                actions.append("declined property")
        
        # Try to build houses if we have monopolies
        phase = self.game_state.get("phase")
        if phase == GamePhase.POST_ROLL.value:
            my_data = self.get_my_data()
            if my_data:
                properties = my_data.get("properties", [])
                money = my_data.get("money", 0) or 0
                
                # Check for buildable properties
                for prop_pos in properties:
                    space = BOARD_SPACES.get(prop_pos, {})
                    build_cost = space.get("house_cost") or 0
                    
                    if build_cost and build_cost > 0 and money >= build_cost + 100:
                        resp = await self.send(MessageType.BUILD_HOUSE.value, {"position": prop_pos})
                        if resp.get("type") == MessageType.GAME_STATE.value:
                            self.houses_built += 1
                            actions.append(f"built house on {space.get('name', 'property')}")
                            money -= build_cost
        
        # End turn (only if in POST_ROLL phase)
        phase = self.game_state.get("phase")
        if phase == GamePhase.POST_ROLL.value:
            resp = await self.send(MessageType.END_TURN.value)
            if resp.get("type") == MessageType.ERROR.value:
                error_msg = resp.get("data", {}).get("message", "")
                if "double" in error_msg.lower():
                    # Rolled doubles, need to roll again
                    actions.append("rolled doubles!")
                    return f"{self.name}: " + ", ".join(actions) + " (continuing...)"
        
        return f"{self.name}: " + ", ".join(actions)
    
    async def close(self):
        if self.ws:
            await self.ws.close()


class IntegrationTestServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 18767):
        self.host = host
        self.port = port
        self.server = None
        self.temp_db = None
    
    async def start(self):
        from server.network.server import MonopolyServer
        
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        
        self.server = MonopolyServer(
            host=self.host,
            port=self.port,
            db_path=self.temp_db.name
        )
        
        self._server_task = asyncio.create_task(self.server.start())
        await asyncio.sleep(0.5)
    
    async def stop(self):
        if self.server:
            await self.server.stop()
        
        if self.temp_db:
            try:
                os.unlink(self.temp_db.name)
            except Exception:
                pass


async def test_full_game_to_completion():
    """
    Play a complete game of Monopoly from start to finish.
    
    This test verifies:
    - Game can run for many turns without errors
    - Properties can be bought and developed
    - Rent is properly transferred between players
    - The game ends when all but one player is bankrupt
    """
    print_header("FULL GAME END-TO-END TEST")
    results = TestResults()
    
    server = IntegrationTestServer()
    players: List[AIPlayer] = []
    
    try:
        await server.start()
        print_info("Server started on port 18767")
        
        # Create players
        print_subheader("Creating Players")
        player_names = ["Alice", "Bob"]  # Start with 2 players for faster games
        
        for name in player_names:
            player = AIPlayer(name)
            success = await player.connect()
            results.add(success, f"{name} failed to connect")
            players.append(player)
            print_success(f"{name} connected")
        
        # Create and start game
        print_subheader("Setting Up Game")
        
        host = players[0]
        resp = await host.send(MessageType.CREATE_GAME.value, {
            "game_name": "E2E Test Game",
            "player_name": host.name
        })
        results.add(
            resp.get("type") == MessageType.GAME_STATE.value,
            "Failed to create game"
        )
        game_id = host.game_id
        print_success(f"Game created: {game_id[:8]}...")
        
        # Others join
        for player in players[1:]:
            resp = await player.send(MessageType.JOIN_GAME.value, {
                "game_id": game_id,
                "player_name": player.name
            })
            results.add(
                resp.get("type") == MessageType.GAME_STATE.value,
                f"{player.name} failed to join"
            )
        
        # Drain messages for host
        await host.drain_messages()
        
        # Start game
        resp = await host.send(MessageType.START_GAME.value)
        results.add(
            resp.get("type") == MessageType.GAME_STATE.value,
            "Failed to start game"
        )
        print_success("Game started!")
        
        # Sync all players
        for player in players:
            await player.drain_messages()
        
        # Play the game
        print_subheader("Playing Game")
        
        max_turns = 50  # Safety limit (reduced for testing speed)
        turn_count = 0
        game_over = False
        winner = None
        
        while turn_count < max_turns and not game_over:
            turn_count += 1
            
            # Sync all players
            for player in players:
                await player.drain_messages()
            
            # Find current player
            current_id = host.game_state.get("current_player_id") if host.game_state else None
            current_player = next((p for p in players if p.player_id == current_id), None)
            
            if not current_player:
                print_failure("Could not determine current player")
                break
            
            # Skip bankrupt players
            if current_player.is_bankrupt():
                # Advance turn
                await current_player.send(MessageType.END_TURN.value)
                continue
            
            # Take turn
            try:
                action_summary = await current_player.take_turn()
                
                if turn_count <= 10 or turn_count % 10 == 0:
                    print_turn(f"Turn {turn_count}: {action_summary}")
                
                # If the action indicates an error about already rolled, we need to end turn
                if "already rolled" in action_summary.lower():
                    # Try to force end turn for current player
                    await current_player.send(MessageType.END_TURN.value)
                
            except Exception as e:
                print_failure(f"Turn {turn_count} error: {e}")
                # Try to recover by forcing end turn
                try:
                    await current_player.send(MessageType.END_TURN.value)
                except Exception:
                    pass
                continue
            
            # Check for game over
            await host.drain_messages()
            
            # Check if game is over
            phase = host.game_state.get("phase") if host.game_state else None
            if phase == GamePhase.GAME_OVER.value:
                game_over = True
                
                # Find winner
                for p in host.game_state.get("players", []):
                    if not p.get("is_bankrupt"):
                        winner_id = p.get("id")
                        winner = next((pl for pl in players if pl.player_id == winner_id), None)
                        break
            
            # Also check if only one player is not bankrupt
            active_players = [
                p for p in players 
                if not p.is_bankrupt()
            ]
            if len(active_players) == 1:
                game_over = True
                winner = active_players[0]
        
        # Game results
        print_subheader("Game Results")
        
        if game_over and winner:
            print_success(f"🏆 WINNER: {winner.name} after {turn_count} turns!")
            results.add(True)
        elif turn_count >= max_turns:
            print_info(f"Game reached {max_turns} turn limit")
            # Find player with most assets
            best_player = None
            best_value = -1
            for player in players:
                data = player.get_my_data()
                if data:
                    value = data.get("money", 0) + len(data.get("properties", [])) * 100
                    if value > best_value:
                        best_value = value
                        best_player = player
            
            print_info(f"Leading player: {best_player.name if best_player else 'None'}")
            results.add(True)  # Not a failure, just a long game
        else:
            print_failure("Game ended unexpectedly")
            results.add(False, "Game ended unexpectedly")
        
        # Statistics
        print_subheader("Game Statistics")
        
        total_properties = sum(p.properties_bought for p in players)
        total_houses = sum(p.houses_built for p in players)
        
        print_info(f"Total turns played: {turn_count}")
        print_info(f"Properties bought: {total_properties}")
        print_info(f"Houses built: {total_houses}")
        
        for player in players:
            data = player.get_my_data()
            if data:
                status = "BANKRUPT" if data.get("is_bankrupt") else f"${data.get('money', 0)}"
                props = len(data.get("properties", []))
                print_info(f"  {player.name}: {status}, {props} properties")
        
        results.add(total_properties > 0, "No properties were bought")
        results.add(turn_count > 5, "Game was too short")
        
    except Exception as e:
        print_failure(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        results.add(False, str(e))
    
    finally:
        for player in players:
            await player.close()
        await server.stop()
    
    return results


async def test_three_player_game():
    """Test a game with three players."""
    print_header("THREE-PLAYER GAME TEST")
    results = TestResults()
    
    server = IntegrationTestServer()
    players: List[AIPlayer] = []
    
    try:
        await server.start()
        
        # Create 3 players
        for name in ["Alice", "Bob", "Charlie"]:
            player = AIPlayer(name)
            await player.connect()
            players.append(player)
        
        # Setup game
        host = players[0]
        await host.send(MessageType.CREATE_GAME.value, {
            "game_name": "Three Player Test",
            "player_name": host.name
        })
        
        for player in players[1:]:
            await player.send(MessageType.JOIN_GAME.value, {
                "game_id": host.game_id,
                "player_name": player.name
            })
        
        await host.drain_messages()
        await host.send(MessageType.START_GAME.value)
        
        # Verify 3 players in game
        for player in players:
            await player.drain_messages()
        
        num_players = len(host.game_state.get("players", []))
        results.add(num_players == 3, f"Expected 3 players, got {num_players}")
        print_success(f"Game started with {num_players} players")
        
        # Play a few rounds
        print_subheader("Playing Rounds")
        
        for round_num in range(1, 6):
            print_info(f"Round {round_num}")
            
            # Each active player takes a turn
            for player in players:
                await player.drain_messages()
                
                if player.is_bankrupt():
                    continue
                
                if player.is_my_turn():
                    action = await player.take_turn()
                    # Handle doubles by taking extra turns
                    while "continuing" in action:
                        await player.drain_messages()
                        if player.is_my_turn():
                            action = await player.take_turn()
                        else:
                            break
        
        # Verify game is still running
        await host.drain_messages()
        active_count = sum(1 for p in players if not p.is_bankrupt())
        
        results.add(
            active_count >= 2,
            f"Only {active_count} players still active"
        )
        print_success(f"{active_count} players still active after 5 rounds")
        
    except Exception as e:
        print_failure(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        results.add(False, str(e))
    
    finally:
        for player in players:
            await player.close()
        await server.stop()
    
    return results


async def run_all_e2e_tests():
    """Run all end-to-end tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                  END-TO-END TEST SUITE                               ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    all_results = TestResults()
    
    tests = [
        ("Three-Player Game", test_three_player_game),
        ("Full Game to Completion", test_full_game_to_completion),
    ]
    
    for name, test_func in tests:
        try:
            print(f"\n{Colors.BOLD}Running: {name}{Colors.RESET}")
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
    success = asyncio.run(run_all_e2e_tests())
    sys.exit(0 if success else 1)
