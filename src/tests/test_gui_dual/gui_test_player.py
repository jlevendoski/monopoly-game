#!/usr/bin/env python3
"""
GUI Test Player - A standalone GUI client that can be controlled via IPC.

This script launches a PyQt6 Monopoly client and listens for commands
via a control socket. This allows test scripts to automate GUI interactions.

Usage:
    python gui_test_player.py --name "Player1" --control-port 19000

The control socket accepts JSON commands like:
    {"action": "connect"}
    {"action": "create_game", "name": "Test Game"}
    {"action": "join_game", "game_id": "xxx"}
    {"action": "start_game"}
    {"action": "roll_dice"}
    {"action": "buy_property"}
    {"action": "decline_property"}
    {"action": "end_turn"}
    {"action": "get_state"}
    {"action": "quit"}
"""

import asyncio
import json
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

try:
    import qasync
except ImportError:
    print("Please install qasync: pip install qasync")
    sys.exit(1)

from client.gui import MainWindow
from client.config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ControlServer(QObject):
    """
    Async server that receives commands and controls the GUI.
    
    Emits signals to interact with the Qt event loop safely.
    """
    
    command_received = pyqtSignal(dict)
    
    def __init__(self, port: int, parent=None):
        super().__init__(parent)
        self.port = port
        self.server = None
        self.client_writer = None
    
    async def start(self):
        """Start the control server."""
        self.server = await asyncio.start_server(
            self._handle_client,
            '127.0.0.1',
            self.port
        )
        logger.info(f"Control server listening on port {self.port}")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a control client connection."""
        self.client_writer = writer
        logger.info("Control client connected")
        
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                
                try:
                    command = json.loads(data.decode().strip())
                    logger.info(f"Received command: {command}")
                    self.command_received.emit(command)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    await self._send_response({"error": str(e)})
        except Exception as e:
            logger.error(f"Control client error: {e}")
        finally:
            writer.close()
            self.client_writer = None
            logger.info("Control client disconnected")
    
    async def _send_response(self, response: dict):
        """Send response to control client."""
        if self.client_writer:
            try:
                data = json.dumps(response) + "\n"
                self.client_writer.write(data.encode())
                await self.client_writer.drain()
            except Exception as e:
                logger.error(f"Failed to send response: {e}")
    
    def send_response_sync(self, response: dict):
        """Send response synchronously (from Qt slot)."""
        if self.client_writer:
            asyncio.ensure_future(self._send_response(response))
    
    async def stop(self):
        """Stop the control server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()


class ControllableMainWindow(MainWindow):
    """
    Extended MainWindow that can be controlled via external commands.
    """
    
    def __init__(self, player_name: str, control_server: ControlServer):
        super().__init__()
        self._control_server = control_server
        self._player_name = player_name
        self._pending_response = None
        
        # Connect control server signals
        control_server.command_received.connect(self._handle_command)
        
        # Track state for reporting
        self._last_game_state = None
        
        # Override message handler to capture state
        original_handler = self._on_message_received
        def patched_handler(data):
            if data.get("type") == "GAME_STATE":
                self._last_game_state = data.get("data")
            original_handler(data)
        self._on_message_received = patched_handler
    
    def _handle_command(self, command: dict):
        """Handle a command from the control server."""
        action = command.get("action", "")
        logger.info(f"Handling command: {action}")
        
        try:
            if action == "connect":
                self._do_connect()
            elif action == "create_game":
                game_name = command.get("name", f"{self._player_name}'s Game")
                self._do_create_game(game_name)
            elif action == "join_game":
                game_id = command.get("game_id")
                if game_id:
                    self._do_join_game(game_id)
                else:
                    self._send_error("game_id required")
            elif action == "start_game":
                self._do_start_game()
            elif action == "roll_dice":
                self._do_roll_dice()
            elif action == "buy_property":
                self._do_buy_property()
            elif action == "decline_property":
                self._do_decline_property()
            elif action == "end_turn":
                self._do_end_turn()
            elif action == "pay_bail":
                self._do_pay_bail()
            elif action == "get_state":
                self._send_state()
            elif action == "quit":
                self._do_quit()
            else:
                self._send_error(f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"Command error: {e}")
            self._send_error(str(e))
    
    def _send_response(self, response: dict):
        """Send response to control client."""
        self._control_server.send_response_sync(response)
    
    def _send_error(self, message: str):
        """Send error response."""
        self._send_response({"success": False, "error": message})
    
    def _send_success(self, data: dict = None):
        """Send success response."""
        response = {"success": True}
        if data:
            response.update(data)
        self._send_response(response)
    
    def _send_state(self):
        """Send current game state."""
        self._send_response({
            "success": True,
            "connected": self._client.is_connected,
            "in_game": self._in_game,
            "is_host": self._is_host,
            "player_id": self._client.player_id,
            "game_id": self._client.current_game_id,
            "game_state": self._last_game_state
        })
    
    def _do_connect(self):
        """Connect to server."""
        async def connect():
            success = await self._client.connect(self._player_name)
            self._send_response({
                "success": success,
                "player_id": self._client.player_id
            })
        asyncio.ensure_future(connect())
    
    def _do_create_game(self, game_name: str):
        """Create a new game."""
        async def create():
            result = await self._client.create_game(game_name)
            if result:
                self._is_host = True
                self._last_game_state = result
                self._send_response({
                    "success": True,
                    "game_id": result.get("game_id")
                })
            else:
                self._send_error("Failed to create game")
        asyncio.ensure_future(create())
    
    def _do_join_game(self, game_id: str):
        """Join an existing game."""
        async def join():
            result = await self._client.join_game(game_id)
            if result:
                self._is_host = False
                self._last_game_state = result
                self._send_success({"game_id": game_id})
            else:
                self._send_error("Failed to join game")
        asyncio.ensure_future(join())
    
    def _do_start_game(self):
        """Start the game."""
        async def start():
            result = await self._client.start_game()
            if result:
                self._in_game = True
                self._last_game_state = result
                self._send_success()
            else:
                self._send_error("Failed to start game")
        asyncio.ensure_future(start())
    
    def _do_roll_dice(self):
        """Roll dice."""
        async def roll():
            result = await self._client.roll_dice()
            if result:
                self._last_game_state = result
                self._send_response({
                    "success": True,
                    "dice": result.get("last_dice_roll", [])
                })
            else:
                self._send_error("Failed to roll dice")
        asyncio.ensure_future(roll())
    
    def _do_buy_property(self):
        """Buy property."""
        async def buy():
            result = await self._client.buy_property()
            if result:
                self._last_game_state = result
                self._send_success()
            else:
                self._send_error("Failed to buy property")
        asyncio.ensure_future(buy())
    
    def _do_decline_property(self):
        """Decline property."""
        async def decline():
            result = await self._client.decline_property()
            if result:
                self._last_game_state = result
                self._send_success()
            else:
                self._send_error("Failed to decline property")
        asyncio.ensure_future(decline())
    
    def _do_end_turn(self):
        """End turn."""
        async def end():
            result = await self._client.end_turn()
            if result:
                self._last_game_state = result
                self._send_success()
            else:
                self._send_error("Failed to end turn")
        asyncio.ensure_future(end())
    
    def _do_pay_bail(self):
        """Pay bail."""
        async def pay():
            result = await self._client.pay_bail()
            if result:
                self._last_game_state = result
                self._send_success()
            else:
                self._send_error("Failed to pay bail")
        asyncio.ensure_future(pay())
    
    def _do_quit(self):
        """Quit the application."""
        self._send_success({"message": "Quitting"})
        QTimer.singleShot(100, QApplication.quit)


async def main_async(control_server: ControlServer):
    """Async main loop."""
    await control_server.start()
    
    # Keep running
    while True:
        await asyncio.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="GUI Test Player")
    parser.add_argument("--name", default="TestPlayer", help="Player name")
    parser.add_argument("--control-port", type=int, default=19000, help="Control port")
    parser.add_argument("--server-host", default="localhost", help="Game server host")
    parser.add_argument("--server-port", type=int, default=8765, help="Game server port")
    args = parser.parse_args()
    
    # Update client settings
    import os
    os.environ["MONOPOLY_SERVER_HOST"] = args.server_host
    os.environ["MONOPOLY_SERVER_PORT"] = str(args.server_port)
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(f"Monopoly - {args.name}")
    
    # Set up async event loop with Qt
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create control server
    control_server = ControlServer(args.control_port)
    
    # Create main window
    window = ControllableMainWindow(args.name, control_server)
    window.setWindowTitle(f"Monopoly - {args.name}")
    window.show()
    
    # Run
    with loop:
        try:
            loop.run_until_complete(main_async(control_server))
        except KeyboardInterrupt:
            pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
