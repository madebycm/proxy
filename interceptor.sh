#!/bin/bash
# Interceptor Script for HTTP Response Mocking
# Based on the proxy.sh infrastructure

# Get the directory where the script is located
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$WORK_DIR/venv"
PROXY_PORT=4646  # Using a different port than the main proxy
PROXY_HOST=127.0.0.1

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -i :"$port" > /dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to find an available port starting from the given port
find_available_port() {
    local port=$1
    local max_attempts=10
    local attempts=0
    
    while check_port "$port" && [ "$attempts" -lt "$max_attempts" ]; do
        port=$((port + 1))
        attempts=$((attempts + 1))
    done
    
    if [ "$attempts" -eq "$max_attempts" ]; then
        echo "Could not find an available port after $max_attempts attempts."
        return 1
    fi
    
    echo "$port"
    return 0
}

# Create log directory if it doesn't exist
mkdir -p "$WORK_DIR/logs"

# Function to install mitmproxy certificate
install_certificate() {
    echo "[*] Checking for mitmproxy certificate..."
    CERT_PATH="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"
    
    if [ -f "$CERT_PATH" ]; then
        echo "[*] Installing mitmproxy certificate to system keychain..."
        # Convert PEM to P12 format
        TMP_CERT="/tmp/mitmproxy-ca.p12"
        PASSWORD="mitmproxy"
        
        # First convert to P12 format if not already done
        if [ ! -f "$TMP_CERT" ]; then
            openssl pkcs12 -export -inkey "$CERT_PATH" -in "$CERT_PATH" -out "$TMP_CERT" -password pass:"$PASSWORD" 2>/dev/null
        fi
        
        # Install to keychain and trust
        echo "[!] You may be prompted for your password to install certificates"
        sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$CERT_PATH" 2>/dev/null
        echo "[+] Certificate installed to system keychain"
    else
        echo "[!] mitmproxy certificate not found. Start mitmproxy at least once to generate it."
        echo "[!] After generating, run this script again with --install-cert"
    fi
}

# Function to configure system proxy for all network interfaces
configure_proxy() {
    echo "==== Configuring System Proxy for Interceptor ===="
    
    # Get all active network services
    NETWORK_SERVICES=$(networksetup -listallnetworkservices | grep -v "*" | grep -v "^$")
    
    # Store original settings to restore later
    mkdir -p "$WORK_DIR/logs/network_backup"
    
    # Configure proxy for ALL network interfaces
    echo "[*] Configuring ALL network interfaces to use $PROXY_HOST:$PROXY_PORT..."
    
    # Loop through all network services
    while IFS= read -r service; do
        echo "[*] Configuring $service"
        
        # Backup original settings
        networksetup -getwebproxy "$service" > "$WORK_DIR/logs/network_backup/${service// /_}_http.txt" 2>/dev/null
        networksetup -getsecurewebproxy "$service" > "$WORK_DIR/logs/network_backup/${service// /_}_https.txt" 2>/dev/null
        
        # Set HTTP and HTTPS proxy
        networksetup -setwebproxy "$service" $PROXY_HOST $PROXY_PORT 2>/dev/null
        networksetup -setsecurewebproxy "$service" $PROXY_HOST $PROXY_PORT 2>/dev/null
        
        # Enable proxy
        networksetup -setwebproxystate "$service" on 2>/dev/null
        networksetup -setsecurewebproxystate "$service" on 2>/dev/null
        
        # Set bypass domains
        networksetup -setproxybypassdomains "$service" "localhost" "127.0.0.1" "::1" 2>/dev/null
    done <<< "$NETWORK_SERVICES"
    
    echo "[+] System proxy configured to use $PROXY_HOST:$PROXY_PORT on all interfaces"
    echo "======================================================"
}

# Function to restore original proxy settings
restore_proxy() {
    echo "==== Restoring Original Proxy Settings ===="
    
    # Get all active network services
    NETWORK_SERVICES=$(networksetup -listallnetworkservices | grep -v "*" | grep -v "^$")
    
    # Restore settings for all network interfaces
    echo "[*] Restoring original proxy settings for all interfaces..."
    
    # Loop through all network services
    while IFS= read -r service; do
        echo "[*] Restoring settings for $service"
        
        # Disable proxy
        networksetup -setwebproxystate "$service" off 2>/dev/null
        networksetup -setsecurewebproxystate "$service" off 2>/dev/null
        
    done <<< "$NETWORK_SERVICES"
    
    echo "[+] System proxy settings restored for all interfaces"
    echo "====================================="
}

# Function to stop the interceptor
stop_interceptor() {
    echo "==== Stopping Interceptor ===="
    
    # Kill the interceptor process if PID file exists
    if [ -f "$WORK_DIR/logs/interceptor.pid" ]; then
        PROXY_PID=$(cat "$WORK_DIR/logs/interceptor.pid")
        echo "[*] Stopping interceptor (PID: $PROXY_PID)..."
        kill $PROXY_PID 2>/dev/null || true
        rm "$WORK_DIR/logs/interceptor.pid"
        echo "[+] Interceptor stopped"
    else
        echo "[!] No interceptor process running (PID file not found)"
    fi
    
    # Restore proxy settings
    restore_proxy
    
    echo "[+] Interceptor session ended"
    echo "=============================="
}

# Function to start the interceptor
start_interceptor() {
    cd "$WORK_DIR"
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Configure system proxy
    configure_proxy
    
    # Start mitmproxy in foreground with our interceptor script
    echo "[*] Starting interceptor on $PROXY_HOST:$PROXY_PORT..."
    echo "[*] Using configuration from $WORK_DIR/interceptor.config.yaml"
    echo "[*] Press Ctrl+C to stop the interceptor"
    
    # Create a trap to handle Ctrl+C and restore proxy settings
    trap 'echo ""; echo "[*] Interrupted by user"; restore_proxy; exit 0' INT
    
    # Start mitmproxy with our interceptor script with comprehensive settings
    # --listen-host 0.0.0.0 to accept connections from all interfaces
    # --no-http2 to ensure maximum compatibility with browsers
    # --set block_global=false to allow connections to all domains
    # --ssl-insecure to ignore certificate validation
    # --mode regular to capture all traffic types
    # --set confdir="$WORK_DIR/.mitmproxy" to store certificates in our directory
    mitmdump \
        --listen-host 0.0.0.0 \
        --listen-port $PROXY_PORT \
        -s "$WORK_DIR/interceptor.py" \
        --no-http2 \
        --ssl-insecure \
        --mode regular \
        --set block_global=false \
        --set confdir="$WORK_DIR/.mitmproxy" \
        -q
    
    # This will only execute if mitmproxy exits normally
    restore_proxy
}

# Parse command line arguments
COMMAND="start"  # Default command
AUTO_PORT=true
INSTALL_CERT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        start|stop|restart)
            COMMAND="$1"
            shift
            ;;
        -p|--port)
            PROXY_PORT="$2"
            shift 2
            ;;
        -a|--auto)
            AUTO_PORT=true
            shift
            ;;
        -c|--install-cert)
            INSTALL_CERT=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./interceptor.sh [command] [options]"
            echo ""
            echo "Commands:"
            echo "  start    - Start the interceptor (default)"
            echo "  stop     - Stop the interceptor and restore system settings"
            echo "  restart  - Restart the interceptor"
            echo ""
            echo "Options:"
            echo "  -p, --port PORT    - Specify the port to use (default: 4646)"
            echo "  -a, --auto         - Automatically find an available port if default is in use"
            echo "  -c, --install-cert - Install mitmproxy certificate to system keychain"
            echo "  -h, --help         - Show this help message"
            echo ""
            echo "Edit interceptor.config.yaml to define intercept rules"
            exit 0
            ;;
        *)
            echo "Error: Unknown option '$1'"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
done

# Check if port is in use and handle accordingly
if [ "$AUTO_PORT" = true ] && check_port "$PROXY_PORT" && [ "$COMMAND" = "start" ]; then
    echo "[!] Port $PROXY_PORT is already in use. Finding an available port..."
    NEW_PORT=$(find_available_port "$PROXY_PORT")
    if [ $? -eq 0 ]; then
        echo "[+] Using port $NEW_PORT instead"
        PROXY_PORT="$NEW_PORT"
    else
        echo "[!] $NEW_PORT"
        exit 1
    fi
elif check_port "$PROXY_PORT" && [ "$COMMAND" = "start" ]; then
    echo "[!] Port $PROXY_PORT is already in use. Please choose a different port with --port or use --auto to find an available port."
    exit 1
fi

# Install certificate if requested
if [ "$INSTALL_CERT" = true ]; then
    install_certificate
    
    # If only installing certificate, exit after installation
    if [ "$COMMAND" = "start" ]; then
        echo "[*] Certificate installation complete. Run without --install-cert to start interceptor."
        exit 0
    fi
fi

# Process command
case "$COMMAND" in
    start)
        start_interceptor
        ;;
    stop)
        stop_interceptor
        ;;
    restart)
        stop_interceptor
        sleep 1
        start_interceptor
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        echo "Use --help to see available options"
        exit 1
        ;;
esac

exit 0
