# Server Deployment Guide

## Prerequisites

- Ubuntu/Debian server
- Python 3.11+
- Root access for initial setup

## Deployment Steps

### 1. Initial Server Setup (as root)

```bash
# Upload or clone the repo to /opt/monopoly
git clone https://github.com/YOUR_USERNAME/monopoly-game.git /opt/monopoly

# Run setup script
cd /opt/monopoly
./deploy/setup.sh
```

This will:
- Install Python and dependencies
- Create `monopoly` user
- Set up firewall rules
- Create necessary directories

### 2. Install Application (as monopoly user)

```bash
su - monopoly
cd /opt/monopoly
./deploy/install.sh
```

This will:
- Create Python virtual environment
- Install pip dependencies
- Create data directory

### 3. Enable Service (as root)

```bash
cp /opt/monopoly/deploy/monopoly.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable monopoly
systemctl start monopoly
```

### 4. Verify

```bash
systemctl status monopoly
journalctl -u monopoly -f  # View logs
```

## Updating the Server

```bash
cd /opt/monopoly
git pull

# Restart the service
sudo systemctl restart monopoly
```

## Configuration

Edit the systemd service file to change settings:

```bash
sudo systemctl edit monopoly
```

Or edit `/etc/systemd/system/monopoly.service` directly, then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart monopoly
```

## Logs

```bash
# View live logs
journalctl -u monopoly -f

# View recent logs
journalctl -u monopoly --since "1 hour ago"
```

## Firewall

The setup script opens port 8765. To change:

```bash
sudo ufw delete allow 8765/tcp
sudo ufw allow NEW_PORT/tcp
```
