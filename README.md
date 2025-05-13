# MITM Proxy Tool

A simple tool for intercepting and monitoring HTTP/HTTPS traffic on macOS using mitmproxy. Provides easy-to-use commands for starting, stopping, and monitoring proxy traffic with minimal or detailed output.

## Overview

This tool sets up a man-in-the-middle proxy on your local machine, configures your system to route traffic through it, and provides logging capabilities to inspect HTTP/HTTPS requests and responses.

## Features

- Automatic system proxy configuration
- Full HTTPS interception with certificate installation
- Detailed request/response logging
- Clean shutdown and system restoration
- Live monitoring modes with real-time output
- URL-only view for minimal output (never truncated)
- Automatic port detection to avoid conflicts
- Single unified command interface
- Timestamped log files for each session

## Requirements

- macOS (tested on macOS 10.15+)
- Python 3.8+
- Bash shell

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd proxy
   ```

2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```
   pip install mitmproxy
   ```

## Usage

The tool uses a unified script with multiple commands and options:

```bash
./proxy.sh [command] [options]
```

### Commands

- `start` - Start the proxy in background mode
- `stop` - Stop the proxy and restore system settings
- `restore` - Restore original proxy settings
- `config` - Configure system proxy settings only
- `live` - Start proxy in interactive mode (Ctrl+C to stop)

### Options

- `-p, --port PORT` - Specify a custom port (default: 4545)
- `-a, --auto` - Automatically find an available port if the default is in use (on by default)
- `-v, --verbose` - Show detailed output (for 'live' mode)

### Quick Reference

```bash
./proxy.sh                 # Start in default mode (URL-only view)
./proxy.sh live            # Same as above
./proxy.sh live --verbose  # Start with detailed output
./proxy.sh start           # Start in background mode
./proxy.sh stop            # Stop the proxy
./proxy.sh --port 8080     # Use a specific port
```

### Starting the Proxy

#### Default Mode (Interactive with URL-only view)

```bash
./proxy.sh
# or
./proxy.sh live
```

This will:
1. Configure your system to use the proxy
2. Show only the URLs of outgoing requests with app info
3. Automatically find an available port if needed
4. Restore settings when you press Ctrl+C

#### Background Mode

```bash
./proxy.sh start
```

This will:
1. Configure your system to use the proxy (127.0.0.1:4545)
2. Start mitmproxy in the background
3. Save logs to `logs/proxy.log`

#### Verbose Mode

```bash
./proxy.sh live --verbose
```

This will:
1. Configure your system to use the proxy
2. Start mitmproxy in the foreground with detailed output
3. Restore settings when you press Ctrl+C

### Certificate Installation

For HTTPS interception to work, you need to install and trust the mitmproxy certificate:

1. Visit http://mitm.it in Safari
2. Click on the Apple icon to download the CA certificate
3. Double-click the downloaded certificate
4. In Keychain Access, set the certificate to 'Always Trust'

### Viewing Logs

#### Real-time Logs

To view the proxy logs in real-time:

```bash
tail -f logs/proxy.log
```

#### Session Logs

Each session in URL-only mode also creates a timestamped log file in the `logs` directory:

```bash
ls -l logs/
# Example: 20250513_132129.txt

cat logs/20250513_132129.txt
```

These logs contain the full URLs of all requests made during that session.

### Stopping the Proxy

```bash
./proxy.sh stop
```

This will:
1. Stop the mitmproxy process
2. Restore your original proxy settings

### Other Commands

```bash
./proxy.sh config    # Configure system proxy settings only
./proxy.sh restore   # Restore original proxy settings only
```

## Troubleshooting

- **No traffic in logs**: Make sure the certificate is properly installed and trusted
- **Certificate issues**: Delete any existing mitmproxy certificates in Keychain Access and reinstall
- **Proxy not starting**: The script automatically finds an available port if the default port is in use. If you want to use a specific port, use:
  ```bash
  ./proxy.sh start --port 8080    # Specify a different port
  ```
- **No application info**: Some applications don't provide identifiable User-Agent headers. In these cases, only the URL will be shown without app info.
- **Connection errors**: If you see HTTP/2 protocol errors in the logs, these are typically normal connection terminations and can be safely ignored.

## License

[MIT License](LICENSE)
