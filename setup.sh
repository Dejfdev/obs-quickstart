#!/usr/bin/env bash
# obs-quickstart — macOS/Linux Installer
# Run: bash setup.sh

set -e

echo ""
echo "============================================"
echo "  obs-quickstart - Setup"
echo "  Plug-and-Play OBS Studio Auto-Configurator"
echo "============================================"
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "[ERROR] Python is not installed!"
    echo "Install Python 3.10+ from https://www.python.org/downloads/"
    exit 1
fi
echo "[OK] Python found: $($PYTHON --version)"

# Install dependencies
echo ""
echo "[..] Installing dependencies..."
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install obsws-python
$PYTHON -m pip install speedtest-cli

# Done
echo ""
echo "============================================"
echo "  Setup complete!"
echo ""
echo "  USAGE:"
echo "    $PYTHON -m obs_quickstart.main"
echo ""
echo "  Make sure OBS Studio is running with"
echo "  WebSocket enabled (Tools → WebSocket Server Settings)"
echo "============================================"
echo ""