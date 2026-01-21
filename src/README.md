# Monopoly - Source Code

This is the source code directory. Share this folder with Claude for updates.

## Structure

```
src/
├── client/                 # Client application
│   ├── gui/               # PyQt6 GUI components
│   │   ├── widgets/       # Reusable widgets (board, panels, dialogs)
│   │   ├── lobby_screen.py
│   │   ├── game_screen.py
│   │   └── main_window.py
│   ├── local/             # Local game mode (no server)
│   ├── network/           # WebSocket client
│   └── main.py           # Client entry point
│
├── server/                # Server application
│   ├── game_engine/      # Core game logic
│   ├── network/          # WebSocket server & message handling
│   ├── persistence/      # SQLite database layer
│   └── main.py          # Server entry point
│
├── shared/               # Shared code (client & server)
│   ├── constants.py     # Board data, game constants
│   ├── enums.py         # Enumerations
│   └── protocol.py      # Message definitions
│
├── run_tests.py         # Single-file test suite (drop-in)
└── requirements*.txt    # Dependencies
```

## Running (Development)

From this directory (`src/`):

```bash
# Local game
python -m client.local.local_main

# Server
python -m server.main

# Client  
python -m client.main
```

## Running Tests

The test suite is a single drop-in file `run_tests.py`:

```bash
# Run all tests (~2s)
python run_tests.py

# Quick mode - unit tests only (~0.2s)
python run_tests.py --quick

# Quiet mode (summary only)
python run_tests.py -q
```

The test file can be stored separately and dropped in when needed.

## CLI Options

**Server:**
```bash
python -m server.main --help
python -m server.main --host 0.0.0.0 --port 8765 --log-level DEBUG
```

**Client:**
```bash
python -m client.main --help
python -m client.main --server 192.168.1.100 --port 8765
```

## Building Standalone Executable

To create a distributable .exe (Windows), .app (macOS), or binary (Linux):

### Prerequisites
```bash
pip install pyinstaller
```

### Build Commands
```bash
# Using the build script (recommended)
python build_app.py              # Build with defaults
python build_app.py --clean      # Clean first, then build
python build_app.py --debug      # Include console window for debugging

# Or using PyInstaller directly with the spec file
pyinstaller Monopoly.spec

# Or manual PyInstaller command
pyinstaller --onefile --windowed --name Monopoly client/main.py
```

### Output
- **Windows:** `dist/Monopoly.exe`
- **macOS:** `dist/Monopoly.app`
- **Linux:** `dist/Monopoly`

### Configuration Defaults
Edit `client/config.py` to change default server host/port before building:
```python
server_host: str = "your.server.com"  # Line 14
server_port: int = 8765                # Line 15
```
