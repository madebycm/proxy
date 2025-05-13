#!/bin/bash
# Configure System Proxy
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==== Configuring System Proxy ===="

# Set system proxy settings to use our local proxy
echo "[*] Configuring proxy settings to use 127.0.0.1:4545..."
networksetup -setwebproxy Wi-Fi 127.0.0.1 4545
networksetup -setsecurewebproxy Wi-Fi 127.0.0.1 4545
networksetup -setwebproxystate Wi-Fi on
networksetup -setsecurewebproxystate Wi-Fi on

echo "[+] System proxy configured to use 127.0.0.1:4545"

echo "[*] To restore original proxy settings when done:"
echo "  ./restore_proxy.sh"
echo "======================================================"
