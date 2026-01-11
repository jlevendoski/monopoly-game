#!/bin/bash
# Monopoly Server Installation Script
# Run as 'monopoly' user from /opt/monopoly

set -e

echo "=========================================="
echo " Monopoly Server Installation"
echo "=========================================="

APP_DIR="/opt/monopoly"
cd $APP_DIR

# Create virtual environment
echo ""
echo "[1/3] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies from src/
echo ""
echo "[2/3] Installing Python dependencies..."
pip install --upgrade pip
pip install -r src/requirements-server.txt

# Create data directory
echo ""
echo "[3/3] Creating data directory..."
mkdir -p data
touch data/.gitkeep

echo ""
echo "=========================================="
echo " Installation Complete!"
echo "=========================================="
echo ""
echo "Test the server manually:"
echo "  source venv/bin/activate"
echo "  cd src"
echo "  python -m server.main"
echo ""
echo "Then set up the systemd service as root."
echo "=========================================="
