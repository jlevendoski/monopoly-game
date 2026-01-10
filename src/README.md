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
├── tests/               # Test suites
│
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

# Tests
python -m pytest tests/ -v
```

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
