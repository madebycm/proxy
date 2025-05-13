#!/bin/bash
# Unified Proxy Script
# Combines functionality of start_proxy.sh, stop_proxy.sh, 
# restore_proxy.sh, and configure_system_proxy.sh

# Get the directory where the script is located
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$WORK_DIR/venv"
PROXY_PORT=4545
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

# Function to check logs directory size and ask to clear if needed
check_logs_size() {
    # Get logs directory size in bytes
    if [ -d "$WORK_DIR/logs" ]; then
        LOGS_SIZE=$(du -sb "$WORK_DIR/logs" | cut -f1)
        # Convert to MB for display
        LOGS_SIZE_MB=$(echo "scale=2; $LOGS_SIZE / 1048576" | bc)
        
        # Check if size exceeds 1MB (1048576 bytes)
        if [ "$LOGS_SIZE" -gt 1048576 ]; then
            echo "[!] Logs directory size: ${LOGS_SIZE_MB}MB (exceeds 1MB)"
            read -p "Do you want to clear all log files? (y/n): " CLEAR_LOGS
            if [[ "$CLEAR_LOGS" =~ ^[Yy]$ ]]; then
                echo "[*] Clearing log files..."
                rm -f "$WORK_DIR/logs"/*.txt
                rm -f "$WORK_DIR/logs"/*.log
                echo "[+] Log files cleared"
            else
                echo "[*] Keeping existing log files"
            fi
        fi
    fi
}

# Function to show usage information
show_usage() {
    echo "Usage: ./proxy.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start        - Start the proxy in background mode"
    echo "  stop         - Stop the proxy and restore system settings"
    echo "  restore      - Restore original proxy settings"
    echo "  config       - Configure system proxy settings"
    echo "  live         - Start proxy in interactive mode (Ctrl+C to stop)"
    echo ""
    echo "Options:"
    echo "  -p, --port PORT  - Specify the port to use (default: 4545)"
    echo "  -a, --auto       - Automatically find an available port if default is in use"
    echo "  -v, --verbose    - Show detailed output (for 'live' mode)"
    echo ""
    echo "Examples:"
    echo "  ./proxy.sh start"
    echo "  ./proxy.sh live --port 8080"
    echo "  ./proxy.sh live --verbose"
    echo ""
    echo "Default mode is minimal URL-only view with auto port detection."
    exit 1
}

# Function to configure system proxy
configure_proxy() {
    echo "==== Configuring System Proxy ===="
    
    # Store original network settings to restore later
    networksetup -getwebproxy Wi-Fi > "$WORK_DIR/logs/original_http_proxy.txt"
    networksetup -getsecurewebproxy Wi-Fi > "$WORK_DIR/logs/original_https_proxy.txt"
    
    # Set system proxy settings to use our local proxy
    echo "[*] Configuring proxy settings to use $PROXY_HOST:$PROXY_PORT..."
    networksetup -setwebproxy Wi-Fi $PROXY_HOST $PROXY_PORT
    networksetup -setsecurewebproxy Wi-Fi $PROXY_HOST $PROXY_PORT
    networksetup -setwebproxystate Wi-Fi on
    networksetup -setsecurewebproxystate Wi-Fi on
    
    echo "[+] System proxy configured to use $PROXY_HOST:$PROXY_PORT"
    echo "======================================================"
}

# Function to restore original proxy settings
restore_proxy() {
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
}

# Function to stop the proxy
stop_proxy() {
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
    restore_proxy
}

# Function to start the proxy in background mode
start_proxy() {
    cd "$WORK_DIR"
    
    # Check logs directory size
    check_logs_size
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Configure system proxy
    configure_proxy
    
    # Start mitmproxy in background
    echo "[*] Starting mitmproxy..."
    # Use --no-http2 to prevent URL truncation in HTTP/2 traffic
    mitmdump -v --showhost --flow-detail 3 --listen-port $PROXY_PORT --no-http2 > logs/proxy.log 2>&1 &
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
    echo "  ./proxy.sh stop"
    echo ""
    echo "To view live proxy logs:"
    echo "  tail -f logs/proxy.log"
}

# Function to start the proxy in live mode (verbose output)
start_proxy_live() {
    cd "$WORK_DIR"
    
    # Check logs directory size
    check_logs_size
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Configure system proxy
    configure_proxy
    
    # Start mitmproxy in foreground with verbose output
    echo "[*] Starting mitmproxy in live mode (Ctrl+C to stop)..."
    echo "[*] Proxy configured on $PROXY_HOST:$PROXY_PORT"
    
    # Create a trap to handle Ctrl+C and restore proxy settings
    trap 'echo ""; echo "[*] Interrupted by user"; restore_proxy; exit 0' INT
    
    # Start mitmproxy in foreground
    # Use --no-http2 to prevent URL truncation in HTTP/2 traffic
    mitmdump -v --showhost --flow-detail 3 --listen-port $PROXY_PORT --no-http2
    
    # This will only execute if mitmproxy exits normally
    restore_proxy
}

# Function to start the proxy in minimal mode (only URLs)
start_proxy_minimal() {
    cd "$WORK_DIR"
    
    # Check logs directory size
    check_logs_size
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Configure system proxy
    configure_proxy
    
    # Start mitmproxy in foreground with minimal output
    echo "[*] Starting mitmproxy in minimal mode (Ctrl+C to stop)..."
    echo "[*] Proxy configured on $PROXY_HOST:$PROXY_PORT"
    echo "[*] Showing only URLs of outgoing requests..."
    
    # Create a trap to handle Ctrl+C and restore proxy settings
    trap 'echo ""; echo "[*] Interrupted by user"; restore_proxy; exit 0' INT
    
    # Start mitmproxy with the custom script to show only URLs
    # Use -q to suppress mitmproxy's default output
    mitmdump --listen-port $PROXY_PORT -s "$WORK_DIR/url_only.py" -q
    
    # This will only execute if mitmproxy exits normally
    restore_proxy
}

# Parse command line arguments
COMMAND=""
AUTO_PORT=true  # Auto port detection is now on by default
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        start|stop|restore|config|live)
            COMMAND="$1"
            shift
            ;;
        liveminimal)  # Keep for backward compatibility
            COMMAND="live"
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
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Error: Unknown option '$1'"
            show_usage
            ;;
    esac
done

# Check if a command was provided
if [ -z "$COMMAND" ]; then
    # Default to 'live' mode if no command is provided
    COMMAND="live"
fi

# Check if port is in use and handle accordingly
if [ "$AUTO_PORT" = true ] && check_port "$PROXY_PORT"; then
    echo "[!] Port $PROXY_PORT is already in use. Finding an available port..."
    NEW_PORT=$(find_available_port "$PROXY_PORT")
    if [ $? -eq 0 ]; then
        echo "[+] Using port $NEW_PORT instead"
        PROXY_PORT="$NEW_PORT"
    else
        echo "[!] $NEW_PORT"
        exit 1
    fi
elif check_port "$PROXY_PORT" && [ "$COMMAND" != "stop" ] && [ "$COMMAND" != "restore" ]; then
    echo "[!] Port $PROXY_PORT is already in use. Please choose a different port with --port or use --auto to find an available port."
    exit 1
fi

# Process command
case "$COMMAND" in
    start)
        start_proxy
        ;;
    stop)
        stop_proxy
        ;;
    restore)
        restore_proxy
        ;;
    config)
        configure_proxy
        ;;
    live)
        if [ "$VERBOSE" = true ]; then
            start_proxy_live
        else
            start_proxy_minimal
        fi
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        show_usage
        ;;
esac

exit 0
