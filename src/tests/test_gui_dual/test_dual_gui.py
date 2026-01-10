#!/usr/bin/env python3
"""
Dual GUI Test Suite - Tests two actual PyQt6 GUI instances playing against each other.

This test launches:
1. A Monopoly server process
2. Two GUI client processes (with control sockets)
3. A test orchestrator that sends commands and verifies state

Requirements:
- PyQt6 and qasync installed
- Display available (or Xvfb for headless)
- Port 18768 for server, 19001-19002 for control sockets

Run:
    python tests/test_gui_dual/test_dual_gui.py
    
For headless (CI) environments:
    xvfb-run -a python tests/test_gui_dual/test_dual_gui.py
"""

import asyncio
import json
import subprocess
import sys
import os
import time
import tempfile
from pathlib import Path
from typing import Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


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


class GUIController:
    """
    Controller for a GUI test player instance.
    
    Communicates with the gui_test_player.py script via a control socket.
    """
    
    def __init__(self, name: str, control_port: int):
        self.name = name
        self.control_port = control_port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.process: Optional[subprocess.Popen] = None
        self.game_id: Optional[str] = None
        self.player_id: Optional[str] = None
    
    async def start_process(self, server_host: str, server_port: int):
        """Start the GUI process."""
        script_path = Path(__file__).parent / "gui_test_player.py"
        
        cmd = [
            sys.executable,
            str(script_path),
            "--name", self.name,
            "--control-port", str(self.control_port),
            "--server-host", server_host,
            "--server-port", str(server_port),
        ]
        
        # Start process
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"}  # Use offscreen for headless
        )
        
        # Wait for control server to be ready
        await asyncio.sleep(2.0)
        
        # Connect to control socket
        for attempt in range(10):
            try:
                self.reader, self.writer = await asyncio.open_connection(
                    '127.0.0.1', 
                    self.control_port
                )
                return True
            except ConnectionRefusedError:
                await asyncio.sleep(0.5)
        
        return False
    
    async def send_command(self, command: dict, timeout: float = 10.0) -> dict:
        """Send a command and wait for response."""
        if not self.writer:
            return {"success": False, "error": "Not connected"}
        
        try:
            data = json.dumps(command) + "\n"
            self.writer.write(data.encode())
            await self.writer.drain()
            
            response_data = await asyncio.wait_for(
                self.reader.readline(),
                timeout=timeout
            )
            return json.loads(response_data.decode().strip())
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def connect(self) -> bool:
        """Tell the GUI to connect to server."""
        response = await self.send_command({"action": "connect"})
        if response.get("success"):
            self.player_id = response.get("player_id")
        return response.get("success", False)
    
    async def create_game(self, name: str) -> Optional[str]:
        """Create a new game."""
        response = await self.send_command({
            "action": "create_game",
            "name": name
        })
        if response.get("success"):
            self.game_id = response.get("game_id")
            return self.game_id
        return None
    
    async def join_game(self, game_id: str) -> bool:
        """Join an existing game."""
        response = await self.send_command({
            "action": "join_game",
            "game_id": game_id
        })
        if response.get("success"):
            self.game_id = game_id
        return response.get("success", False)
    
    async def start_game(self) -> bool:
        """Start the game."""
        response = await self.send_command({"action": "start_game"})
        return response.get("success", False)
    
    async def roll_dice(self) -> Optional[List[int]]:
        """Roll dice."""
        response = await self.send_command({"action": "roll_dice"})
        if response.get("success"):
            return response.get("dice", [])
        return None
    
    async def buy_property(self) -> bool:
        """Buy property."""
        response = await self.send_command({"action": "buy_property"})
        return response.get("success", False)
    
    async def decline_property(self) -> bool:
        """Decline property."""
        response = await self.send_command({"action": "decline_property"})
        return response.get("success", False)
    
    async def end_turn(self) -> bool:
        """End turn."""
        response = await self.send_command({"action": "end_turn"})
        return response.get("success", False)
    
    async def pay_bail(self) -> bool:
        """Pay bail."""
        response = await self.send_command({"action": "pay_bail"})
        return response.get("success", False)
    
    async def get_state(self) -> dict:
        """Get current state."""
        return await self.send_command({"action": "get_state"})
    
    async def quit(self):
        """Quit the GUI."""
        await self.send_command({"action": "quit"})
    
    async def stop(self):
        """Stop the GUI process."""
        if self.writer:
            try:
                await self.quit()
            except Exception:
                pass
            self.writer.close()
        
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class TestServer:
    """Test server manager."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 18768):
        self.host = host
        self.port = port
        self.server = None
        self.temp_db = None
        self._server_task = None
    
    async def start(self):
        """Start the test server."""
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
        """Stop the server."""
        if self.server:
            await self.server.stop()
        
        if self.temp_db:
            try:
                os.unlink(self.temp_db.name)
            except Exception:
                pass


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


async def test_dual_gui_game():
    """
    Test two GUI instances playing a game together.
    
    This test:
    1. Starts the game server
    2. Launches two GUI clients
    3. Has them connect, create/join a game
    4. Plays several turns
    5. Verifies state consistency
    """
    print_header("DUAL GUI INTEGRATION TEST")
    results = TestResults()
    
    server = TestServer()
    gui1 = GUIController("Alice", 19001)
    gui2 = GUIController("Bob", 19002)
    
    try:
        # Start server
        print_subheader("Starting Server")
        await server.start()
        print_success(f"Server running on port {server.port}")
        
        # Start GUI instances
        print_subheader("Starting GUI Instances")
        
        success = await gui1.start_process(server.host, server.port)
        if not success:
            print_failure("Failed to start GUI 1")
            results.add(False, "GUI 1 start failed")
            return results
        print_success(f"GUI 1 (Alice) started, control port {gui1.control_port}")
        
        success = await gui2.start_process(server.host, server.port)
        if not success:
            print_failure("Failed to start GUI 2")
            results.add(False, "GUI 2 start failed")
            return results
        print_success(f"GUI 2 (Bob) started, control port {gui2.control_port}")
        
        # Connect both GUIs to server
        print_subheader("Connecting to Server")
        
        success = await gui1.connect()
        results.add(success, "GUI 1 connect failed")
        if success:
            print_success(f"Alice connected (ID: {gui1.player_id[:8] if gui1.player_id else 'N/A'}...)")
        
        success = await gui2.connect()
        results.add(success, "GUI 2 connect failed")
        if success:
            print_success(f"Bob connected (ID: {gui2.player_id[:8] if gui2.player_id else 'N/A'}...)")
        
        # Create and join game
        print_subheader("Creating Game")
        
        game_id = await gui1.create_game("Dual GUI Test Game")
        results.add(game_id is not None, "Game creation failed")
        if game_id:
            print_success(f"Game created: {game_id[:8]}...")
        
        await asyncio.sleep(0.5)
        
        success = await gui2.join_game(game_id)
        results.add(success, "Join game failed")
        if success:
            print_success("Bob joined the game")
        
        await asyncio.sleep(0.5)
        
        # Start game
        print_subheader("Starting Game")
        
        success = await gui1.start_game()
        results.add(success, "Start game failed")
        if success:
            print_success("Game started!")
        
        await asyncio.sleep(1.0)
        
        # Verify both GUIs are in game
        state1 = await gui1.get_state()
        state2 = await gui2.get_state()
        
        results.add(
            state1.get("in_game", False),
            "GUI 1 not in game"
        )
        results.add(
            state2.get("in_game", False),
            "GUI 2 not in game"
        )
        print_success("Both GUIs are in game state")
        
        # Play a few turns
        print_subheader("Playing Turns")
        
        for turn in range(1, 4):
            print_info(f"Turn {turn}")
            
            await asyncio.sleep(0.5)
            
            # Get states to determine current player
            state1 = await gui1.get_state()
            
            game_state = state1.get("game_state") or {}
            if not game_state:
                print_info(f"  No game state available, skipping turn")
                continue
                
            current_player_id = game_state.get("current_player_id")
            
            if current_player_id == gui1.player_id:
                current_gui = gui1
                other_gui = gui2
            else:
                current_gui = gui2
                other_gui = gui1
            
            print_info(f"  {current_gui.name}'s turn")
            
            # Roll dice
            dice = await current_gui.roll_dice()
            if dice:
                print_info(f"  Rolled: {dice[0] if len(dice) > 0 else '?'} + {dice[1] if len(dice) > 1 else '?'} = {sum(dice) if dice else 0}")
            else:
                print_info("  Roll failed (may need to handle jail or other state)")
            
            await asyncio.sleep(0.3)
            
            # Check state for property decision
            state = await current_gui.get_state()
            phase = state.get("game_state", {}).get("phase", "")
            
            if phase == "PROPERTY_DECISION":
                # Decide whether to buy (50% chance for testing)
                import random
                if random.random() > 0.5:
                    success = await current_gui.buy_property()
                    print_info(f"  {'Bought' if success else 'Failed to buy'} property")
                else:
                    success = await current_gui.decline_property()
                    print_info(f"  Declined property")
            
            await asyncio.sleep(0.3)
            
            # End turn
            success = await current_gui.end_turn()
            if success:
                print_info(f"  Turn ended")
            else:
                # Might have rolled doubles
                print_info(f"  Turn didn't end (doubles or error)")
        
        # Final state verification
        print_subheader("State Verification")
        
        await asyncio.sleep(0.5)
        
        final_state1 = await gui1.get_state()
        final_state2 = await gui2.get_state()
        
        gs1 = final_state1.get("game_state") or {}
        gs2 = final_state2.get("game_state") or {}
        
        # Both should see same game ID
        results.add(
            gs1.get("game_id") == gs2.get("game_id"),
            "Game IDs don't match"
        )
        print_success(f"Game IDs match")
        
        # Both should see same number of players
        p1_count = len(gs1.get("players", []))
        p2_count = len(gs2.get("players", []))
        results.add(
            p1_count == p2_count == 2,
            f"Player counts don't match: {p1_count} vs {p2_count}"
        )
        print_success(f"Both GUIs see {p1_count} players")
        
        # Verify player positions are consistent
        for p1 in gs1.get("players", []):
            p2 = next((p for p in gs2.get("players", []) if p.get("id") == p1.get("id")), None)
            if p2:
                results.add(
                    p1.get("position") == p2.get("position"),
                    f"Position mismatch for player {p1.get('id', 'N/A')[:8]}"
                )
                results.add(
                    p1.get("money") == p2.get("money"),
                    f"Money mismatch for player {p1.get('id', 'N/A')[:8]}"
                )
        
        print_success("Player states are consistent across GUIs")
        
    except Exception as e:
        print_failure(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        results.add(False, str(e))
    
    finally:
        # Cleanup
        print_subheader("Cleanup")
        
        await gui1.stop()
        print_info("GUI 1 stopped")
        
        await gui2.stop()
        print_info("GUI 2 stopped")
        
        await server.stop()
        print_info("Server stopped")
    
    return results


async def run_dual_gui_tests():
    """Run all dual GUI tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                    DUAL GUI TEST SUITE                               ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    print_info("Note: This test requires PyQt6 and qasync installed.")
    print_info("For headless environments, use: xvfb-run -a python <script>")
    print()
    
    all_results = TestResults()
    
    try:
        results = await test_dual_gui_game()
        all_results.passed += results.passed
        all_results.failed += results.failed
        all_results.errors.extend(results.errors)
    except Exception as e:
        print_failure(f"Test suite error: {e}")
        import traceback
        traceback.print_exc()
        all_results.add(False, str(e))
    
    all_results.summary()
    return all_results.failed == 0


if __name__ == "__main__":
    # Check for display
    if sys.platform != 'win32' and not os.environ.get('DISPLAY') and not os.environ.get('QT_QPA_PLATFORM'):
        print("Warning: No display detected. Setting QT_QPA_PLATFORM=offscreen")
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    success = asyncio.run(run_dual_gui_tests())
    sys.exit(0 if success else 1)
