# Proxy Monitor UI

A clean, modern web interface for monitoring and controlling your HTTP/HTTPS proxy with real-time request visualization.

## Features

- **Real-time Request Monitoring**: See all HTTP/HTTPS requests as they happen
- **Visual Request Inspector**: Click any request to see full details including headers and responses
- **Proxy Control**: Start/stop proxy with one click
- **Configuration Management**: 
  - Domain blacklist editor
  - Interceptor rules with custom responses
  - Port configuration
- **Search & Filter**: Find requests quickly by URL or method
- **Clean Interface**: Simple, smooth design focused on usability

## Quick Start

1. Install UI dependencies:
```bash
./start_ui.sh
```

2. Open your browser to: http://localhost:5678

3. Click "Start Proxy" to begin monitoring requests

## UI Overview

### Main Dashboard
- **Status Bar**: Shows proxy status, port, request count, and uptime
- **Control Panel**: Start/stop proxy, configure port and mode
- **Request List**: Real-time display of all requests with search/filter

### Configuration Tabs

#### Requests Tab
- View all HTTP/HTTPS requests in real-time
- Click any request for detailed information
- Filter by method (GET, POST, etc.) or search by URL

#### Blacklist Tab
- Add domains to ignore (one per line)
- Useful for filtering out noise from analytics, CDNs, etc.

#### Interceptor Tab
- Create rules to intercept specific URLs
- Define custom responses with status codes and content
- Perfect for testing error scenarios or mocking APIs

## Using the Interceptor

1. Go to the Interceptor tab
2. Click "Add Rule"
3. Enter:
   - **URL Pattern**: e.g., `api.example.com/users`
   - **Status Code**: e.g., `200`
   - **Response Content**: Text or JSON
   - **Content Type**: e.g., `application/json`
4. Click "Save Rules"
5. Restart the proxy for changes to take effect

### Example Interceptor Rule

**URL Pattern**: `api.myapp.com/v1/status`  
**Status**: `503`  
**Content**:
```json
{
  "error": "Service temporarily unavailable",
  "retry_after": 300
}
```
**Content-Type**: `application/json`

## Certificate Installation

For HTTPS traffic monitoring:

1. Start the proxy
2. Click "Install Certificate" button
3. Follow the on-screen instructions
4. Visit http://mitm.it in Safari
5. Download and install the certificate
6. Trust it in Keychain Access

## Keyboard Shortcuts

- `Ctrl/Cmd + K`: Focus search box
- `Escape`: Close modals

## Architecture

- **Backend**: Flask with WebSocket support
- **Frontend**: Vanilla JavaScript with Socket.IO
- **Proxy**: mitmproxy with custom Python scripts
- **Real-time Updates**: WebSocket connection for live request streaming

## Troubleshooting

**Proxy won't start**: Check if port is already in use. Try a different port.

**No requests showing**: Ensure system proxy is configured correctly. Check certificate installation for HTTPS.

**UI not loading**: Make sure Flask dependencies are installed (`pip install -r requirements_ui.txt`)

## API Endpoints

- `GET /api/proxy/state` - Get current proxy status
- `POST /api/proxy/start` - Start proxy with configuration
- `POST /api/proxy/stop` - Stop proxy and restore settings
- `GET /api/config/blacklist` - Get domain blacklist
- `POST /api/config/blacklist` - Update domain blacklist
- `GET /api/config/interceptor` - Get interceptor rules
- `POST /api/config/interceptor` - Update interceptor rules
- `POST /api/logs/clear` - Clear all log files