#!/bin/bash
# Start the Proxy UI

# Get the directory where the script is located
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$WORK_DIR/venv"

echo "==== Starting Proxy UI ===="

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "[!] Virtual environment not found at $VENV_DIR"
    echo "[*] Please run the setup script first"
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install UI requirements if needed
echo "[*] Checking UI dependencies..."
pip install -q -r requirements_ui.txt

# Start the UI server
echo "[*] Starting Proxy UI server..."
echo "[+] Open http://localhost:5678 in your browser"
echo "[+] Press Ctrl+C to stop"
echo ""

python proxy_ui.py