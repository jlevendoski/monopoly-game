# Monopoly Multiplayer

A multiplayer Monopoly game with a central server and PyQt6-based client GUI.

## Project Structure

```
monopoly-game/
├── src/                    # SOURCE CODE (share this with Claude)
│   ├── client/            # Client application
│   ├── server/            # Server application
│   ├── shared/            # Shared code (client & server)
│   ├── tests/             # Test suites
│   └── requirements*.txt  # Python dependencies
│
├── deploy/                # Deployment scripts (server admin only)
│   ├── setup.sh          # Initial server setup
│   ├── install.sh        # App installation
│   └── monopoly.service  # systemd service file
│
├── data/                  # Runtime data (gitignored)
│   └── monopoly.db       # SQLite database
│
└── README.md             # This file
```

## Quick Start

### Development Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/monopoly-game.git
cd monopoly-game

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (for full development)
pip install -r src/requirements-dev.txt

# Or just server/client:
pip install -r src/requirements-server.txt
pip install -r src/requirements-client.txt
```

### Running the Game

#### Local Game (No Server Needed)
```bash
cd src
python -m client.local.local_main
```

#### Online Multiplayer

**Start the server:**
```bash
cd src
python -m server.main

# With custom settings:
python -m server.main --host 0.0.0.0 --port 8765 --log-level DEBUG
```

**Start the client:**
```bash
cd src
python -m client.main

# Connect to remote server:
python -m client.main --server your-server.com --port 8765
```

### Running Tests
```bash
cd src
python -m pytest tests/ -v
```

## Server Deployment

See `deploy/README.md` for full deployment instructions.

Quick version:
```bash
# On server as root:
./deploy/setup.sh

# As monopoly user:
./deploy/install.sh

# As root, enable service:
cp deploy/monopoly.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now monopoly
```

## Configuration

### Server (Environment Variables)
- `SERVER_HOST` - Bind address (default: 0.0.0.0)
- `SERVER_PORT` - Port (default: 8765)
- `DATABASE_PATH` - SQLite path (default: ./data/monopoly.db)
- `LOG_LEVEL` - Logging level (default: INFO)

### Client (Environment Variables)
- `MONOPOLY_SERVER_HOST` - Server host (default: localhost)
- `MONOPOLY_SERVER_PORT` - Server port (default: 8765)

## Working with Claude

When getting code updates from Claude:

1. **Send Claude**: Only the `src/` folder
2. **Receive back**: Updated `src/` folder  
3. **Extract**: Copy contents to your `src/` directory
4. **Commit**: `git add -A && git commit -m "Updates from Claude" && git push`

This keeps your `.git/`, `venv/`, `data/`, and deployment configs intact.
