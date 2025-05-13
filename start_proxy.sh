#!/bin/bash
# Start MITM proxy and configure system
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$WORK_DIR/venv"
cd "$WORK_DIR"

# Create log directory
mkdir -p logs

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Store original network settings to restore later
networksetup -getwebproxy Wi-Fi > logs/original_http_proxy.txt
networksetup -getsecurewebproxy Wi-Fi > logs/original_https_proxy.txt

# Configure system proxy settings
echo "[*] Configuring system proxy settings..."
networksetup -setwebproxy Wi-Fi 127.0.0.1 4545
networksetup -setsecurewebproxy Wi-Fi 127.0.0.1 4545

# Enable proxy
networksetup -setwebproxystate Wi-Fi on
networksetup -setsecurewebproxystate Wi-Fi on

echo "[+] System proxy configured to use 127.0.0.1:4545"

# Start mitmproxy in background
echo "[*] Starting mitmproxy..."
mitmdump -v --showhost --flow-detail 3 --listen-port 4545 > logs/proxy.log 2>&1 &
PROXY_PID=$!
echo $PROXY_PID > logs/proxy.pid

echo "[+] Proxy started with PID $PROXY_PID"
echo "[+] Log file: $WORK_DIR/logs/proxy.log"
echo ""
echo "Certificate Installation Instructions:"
echo "1. Visit http://mitm.it in Safari"
echo "2. Click on the Apple icon to download the CA certificate"
echo "3. Double-click the downloaded certificate"
echo "4. In Keychain Access, set the certificate to 'Always Trust'"
echo ""
echo "To stop the proxy and restore settings:"
echo "  ./stop_proxy.sh"
echo ""
echo "To view live proxy logs:"
echo "  tail -f logs/proxy.log"
