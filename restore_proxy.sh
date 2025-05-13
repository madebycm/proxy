#!/bin/bash
# Restore Original Proxy Settings

echo "==== Restoring Original Proxy Settings ===="
echo "======================================"

# Disable and clear system proxy settings
echo "[*] Restoring original proxy settings..."
networksetup -setwebproxystate Wi-Fi off
networksetup -setsecurewebproxystate Wi-Fi off
networksetup -setwebproxy Wi-Fi "" 0
networksetup -setsecurewebproxy Wi-Fi "" 0

echo "[+] System proxy disabled"
echo "[+] Proxy session ended"
echo "======================================"
