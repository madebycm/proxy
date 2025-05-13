#!/bin/bash
# Stop MITM proxy and restore system settings
WORK_DIR="//Users/0x7f/www/proxy"
cd "$WORK_DIR"

# Kill the proxy process
if [ -f logs/proxy.pid ]; then
    PROXY_PID=$(cat logs/proxy.pid)
    echo "[*] Stopping mitmproxy (PID: $PROXY_PID)..."
    kill $PROXY_PID 2>/dev/null || true
    rm logs/proxy.pid
    echo "[+] Proxy stopped"
else
    echo "[*] No proxy PID file found"
fi

# Restore original proxy settings
echo "[*] Restoring original proxy settings..."
networksetup -setwebproxystate Wi-Fi off
networksetup -setsecurewebproxystate Wi-Fi off
echo "[+] System proxy disabled"

echo "[+] Proxy session ended"
