#!/usr/bin/env python3
"""
GUI Test Against Running Server

This test launches two GUI clients that connect to your already-running server
on the default port (8765). This is the real-world integration test before packaging.

Prerequisites:
    - Server running: python3 -m server.main
    - Display available (or run with appropriate Qt platform)

Usage:
    python3 tests/test_gui_dual/test_gui_against_server.py
    
    # Or specify custom server:
    python3 tests/test_gui_dual/test_gui_against_server.py --host localhost --port 8765
"""

import asyncio
import json
import subprocess
import sys
import os
import argparse
import time
from pathlib import Path
from typing import Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import websockets


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


def print_step(num: int, text: str) -> None:
    print(f"\n  {Colors.BOLD}{Colors.MAGENTA}[Step {num}]{Colors.RESET} {text}")


async def check_server_running(host: str, port: int) -> bool:
    """Check if the server is running and accepting connections."""
    try:
        ws = await asyncio.wait_for(
            websockets.connect(f"ws://{host}:{port}"),
            timeout=5.0
        )
        await ws.close()
        return True
    except Exception:
        return False


async def run_gui_test(host: str, port: int):
    """
    Run the GUI test against the running server.
    
    Launches two client processes and verifies they can play together.
    """
    print_header("GUI TEST AGAINST RUNNING SERVER")
    
    print_info(f"Target server: ws://{host}:{port}")
    
    # Step 1: Verify server is running
    print_subheader("Checking Server")
    
    if not await check_server_running(host, port):
        print_failure(f"Server not responding at ws://{host}:{port}")
        print()
        print_info("Please ensure the server is running:")
        print_info("  python3 -m server.main")
        print()
        return False
    
    print_success(f"Server is running at ws://{host}:{port}")
    
    # Step 2: Launch two GUI clients
    print_subheader("Launching GUI Clients")
    
    env = os.environ.copy()
    env["MONOPOLY_SERVER_HOST"] = host
    env["MONOPOLY_SERVER_PORT"] = str(port)
    
    # Determine python command
    python_cmd = sys.executable
    
    client_script = project_root / "client" / "main.py"
    
    print_step(1, "Starting Client 1 (Alice)...")
    try:
        client1 = subprocess.Popen(
            [python_cmd, "-m", "client.main"],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print_success("Client 1 launched (PID: {})".format(client1.pid))
    except Exception as e:
        print_failure(f"Failed to launch Client 1: {e}")
        return False
    
    await asyncio.sleep(2)  # Give client time to start
    
    print_step(2, "Starting Client 2 (Bob)...")
    try:
        client2 = subprocess.Popen(
            [python_cmd, "-m", "client.main"],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print_success("Client 2 launched (PID: {})".format(client2.pid))
    except Exception as e:
        print_failure(f"Failed to launch Client 2: {e}")
        client1.terminate()
        return False
    
    # Step 3: Interactive testing instructions
    print_subheader("Manual Test Steps")
    
    print(f"""
  {Colors.BOLD}Two GUI windows should now be open. Please perform these steps:{Colors.RESET}

  {Colors.CYAN}In Client 1 (Alice):{Colors.RESET}
    1. Enter name: Alice
    2. Click "Connect"
    3. Click "Create Game"
    4. Enter game name: Test Game
    5. Wait for Bob to join...

  {Colors.CYAN}In Client 2 (Bob):{Colors.RESET}
    1. Enter name: Bob
    2. Click "Connect"
    3. Select "Test Game" from the list
    4. Click "Join"

  {Colors.CYAN}In Client 1 (Alice):{Colors.RESET}
    5. Click "Start Game"

  {Colors.CYAN}Both Clients - Play a few turns:{Colors.RESET}
    6. Current player: Click "Roll Dice"
    7. If on property: Click "Buy" or "Decline"
    8. Click "End Turn"
    9. Repeat for other player
    10. Verify both windows show the same game state

  {Colors.BOLD}Press Enter when testing is complete (or Ctrl+C to abort)...{Colors.RESET}
""")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n")
        print_info("Test aborted by user")
    
    # Step 4: Cleanup
    print_subheader("Cleanup")
    
    print_info("Terminating client processes...")
    
    client1.terminate()
    client2.terminate()
    
    try:
        client1.wait(timeout=5)
        print_success("Client 1 terminated")
    except subprocess.TimeoutExpired:
        client1.kill()
        print_info("Client 1 force killed")
    
    try:
        client2.wait(timeout=5)
        print_success("Client 2 terminated")
    except subprocess.TimeoutExpired:
        client2.kill()
        print_info("Client 2 force killed")
    
    # Step 5: Get user verdict
    print_subheader("Test Result")
    
    print(f"\n  {Colors.BOLD}Did the test pass? (y/n):{Colors.RESET} ", end="")
    try:
        response = input().strip().lower()
        if response in ('y', 'yes'):
            print_success("GUI test PASSED")
            return True
        else:
            print_failure("GUI test FAILED")
            return False
    except (KeyboardInterrupt, EOFError):
        print()
        print_info("No response, assuming test incomplete")
        return False


async def run_automated_websocket_test(host: str, port: int):
    """
    Run an automated test using direct WebSocket connections.
    
    This doesn't test the GUI itself, but verifies the client-server
    protocol works correctly with two simultaneous connections.
    """
    print_header("AUTOMATED PROTOCOL TEST (No GUI)")
    
    print_info(f"Target server: ws://{host}:{port}")
    print_info("This test verifies the protocol without launching GUI windows")
    
    # Check server
    if not await check_server_running(host, port):
        print_failure(f"Server not responding at ws://{host}:{port}")
        return False
    
    print_success("Server is running")
    
    import uuid
    from shared.enums import MessageType
    
    print_subheader("Connecting Two Players")
    
    # Connect player 1
    ws1 = await websockets.connect(f"ws://{host}:{port}")
    p1_id = str(uuid.uuid4())
    await ws1.send(json.dumps({
        "type": MessageType.CONNECT.value,
        "data": {"player_id": p1_id, "player_name": "Alice"}
    }))
    resp = json.loads(await ws1.recv())
    if resp.get("data", {}).get("success"):
        print_success("Alice connected")
    else:
        print_failure("Alice failed to connect")
        return False
    
    # Connect player 2
    ws2 = await websockets.connect(f"ws://{host}:{port}")
    p2_id = str(uuid.uuid4())
    await ws2.send(json.dumps({
        "type": MessageType.CONNECT.value,
        "data": {"player_id": p2_id, "player_name": "Bob"}
    }))
    resp = json.loads(await ws2.recv())
    if resp.get("data", {}).get("success"):
        print_success("Bob connected")
    else:
        print_failure("Bob failed to connect")
        return False
    
    print_subheader("Creating and Joining Game")
    
    # Alice creates game
    await ws1.send(json.dumps({
        "type": MessageType.CREATE_GAME.value,
        "data": {"game_name": "Protocol Test", "player_name": "Alice"}
    }))
    resp = json.loads(await ws1.recv())
    if resp.get("type") == MessageType.GAME_STATE.value:
        game_id = resp.get("data", {}).get("game_id")
        print_success(f"Game created: {game_id[:8]}...")
    else:
        print_failure("Failed to create game")
        return False
    
    # Bob joins game
    await ws2.send(json.dumps({
        "type": MessageType.JOIN_GAME.value,
        "data": {"game_id": game_id, "player_name": "Bob"}
    }))
    resp = json.loads(await ws2.recv())
    if resp.get("type") == MessageType.GAME_STATE.value:
        print_success("Bob joined game")
    else:
        print_failure("Bob failed to join")
        return False
    
    # Drain Alice's notification
    try:
        await asyncio.wait_for(ws1.recv(), timeout=1.0)
    except asyncio.TimeoutError:
        pass
    
    print_subheader("Starting Game")
    
    # Alice starts game
    await ws1.send(json.dumps({
        "type": MessageType.START_GAME.value,
        "data": {}
    }))
    resp = json.loads(await ws1.recv())
    if resp.get("type") == MessageType.GAME_STATE.value:
        print_success("Game started")
    else:
        print_failure("Failed to start game")
        return False
    
    # Drain Bob's notification
    try:
        await asyncio.wait_for(ws2.recv(), timeout=1.0)
    except asyncio.TimeoutError:
        pass
    
    print_subheader("Playing One Turn")
    
    # Determine current player and roll dice
    game_state = resp.get("data", {})
    current_player_id = game_state.get("current_player_id")
    
    current_ws = ws1 if current_player_id == p1_id else ws2
    current_name = "Alice" if current_player_id == p1_id else "Bob"
    
    await current_ws.send(json.dumps({
        "type": MessageType.ROLL_DICE.value,
        "data": {}
    }))
    resp = json.loads(await current_ws.recv())
    if resp.get("type") == MessageType.GAME_STATE.value:
        dice = resp.get("data", {}).get("last_dice_roll", [])
        print_success(f"{current_name} rolled {dice}")
    else:
        print_failure("Failed to roll dice")
        return False
    
    # Cleanup
    print_subheader("Cleanup")
    
    await ws1.close()
    await ws2.close()
    print_success("Connections closed")
    
    print_subheader("Result")
    print_success("Automated protocol test PASSED")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="GUI Test Against Running Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test against server
    python3 tests/test_gui_dual/test_gui_against_server.py --server myserver.example.com
    
    # Test against server with custom port
    python3 tests/test_gui_dual/test_gui_against_server.py --server myserver.example.com --port 9000
    
    # Run automated protocol test only (no GUI)
    python3 tests/test_gui_dual/test_gui_against_server.py --server myserver.example.com --protocol-only
"""
    )
    parser.add_argument("--server", required=True, help="Server address (required)")
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    parser.add_argument("--protocol-only", action="store_true", 
                       help="Run automated protocol test without launching GUI")
    
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║              GUI TEST AGAINST RUNNING SERVER                         ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    if args.protocol_only:
        success = asyncio.run(run_automated_websocket_test(args.server, args.port))
    else:
        success = asyncio.run(run_gui_test(args.server, args.port))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
