#!/bin/bash
# Configure System Proxy

echo "==== Configuring System Proxy ===="

# Set system proxy settings to use our local proxy
echo "[*] Configuring proxy settings to use 127.0.0.1:8080..."
networksetup -setwebproxy Wi-Fi 127.0.0.1 8080
networksetup -setsecurewebproxy Wi-Fi 127.0.0.1 8080
networksetup -setwebproxystate Wi-Fi on
networksetup -setsecurewebproxystate Wi-Fi on

echo "[+] System proxy configured to use 127.0.0.1:8080"

echo "[*] To restore original proxy settings when done:"
echo "  ./restore_proxy.sh"
echo "======================================================"
