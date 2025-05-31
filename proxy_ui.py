#!/usr/bin/env python3
import os
import sys
import json
import yaml
import subprocess
import threading
import queue
import signal
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from werkzeug.serving import make_server
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
proxy_process = None
proxy_thread = None
request_queue = queue.Queue()
proxy_state = {
    'running': False,
    'port': 4545,
    'mode': 'minimal',
    'requests_count': 0,
    'start_time': None
}

# Get the working directory
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(WORK_DIR, 'venv')

def emit_proxy_state():
    """Emit current proxy state to all connected clients"""
    socketio.emit('proxy_state', proxy_state)

def emit_request(request_data):
    """Emit a new request to all connected clients"""
    socketio.emit('new_request', request_data)

def read_config_file(filename):
    """Read a configuration file"""
    filepath = os.path.join(WORK_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return f.read()
    return ""

def write_config_file(filename, content):
    """Write a configuration file"""
    filepath = os.path.join(WORK_DIR, filename)
    with open(filepath, 'w') as f:
        f.write(content)

def parse_request_line(line):
    """Parse a request line from mitmproxy output"""
    import re
    from urllib.parse import urlparse
    
    try:
        # Parse lines like: [12:34:56] GET https://example.com/api/data [Chrome]
        if not line.strip():
            return None
            
        # Check if it's a response line
        if '└─ Response:' in line:
            parts = line.split('└─ Response:', 1)
            if len(parts) > 1:
                timestamp_part = parts[0].strip()
                response_part = parts[1].strip()
                
                # Extract timestamp
                timestamp_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', timestamp_part)
                timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().strftime("%H:%M:%S")
                
                # Parse response details
                status_match = re.search(r'(\d{3})', response_part)
                status = status_match.group(1) if status_match else 'unknown'
                
                return {
                    'type': 'response',
                    'timestamp': timestamp,
                    'status': status,
                    'content_type': response_part.split(status, 1)[1].strip() if status in response_part else ''
                }
        
        # Parse request lines
        match = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s+(\w+)\s+(.+?)(?:\s+\[(.+?)\])?$', line)
        if match:
            timestamp, method, url, app = match.groups()
            
            # Parse URL to get host and path
            parsed = urlparse(url)
            
            return {
                'type': 'request',
                'timestamp': timestamp,
                'method': method,
                'url': url,
                'host': parsed.netloc,
                'path': parsed.path + ('?' + parsed.query if parsed.query else ''),
                'app': app or 'Unknown',
                'id': f"{timestamp}_{method}_{parsed.netloc}"
            }
    except Exception as e:
        logger.error(f"Error parsing line: {e}")
    
    return None

def monitor_proxy_output():
    """Monitor proxy output and emit requests via WebSocket"""
    global proxy_process, proxy_state
    
    while proxy_state['running'] and proxy_process:
        try:
            line = proxy_process.stdout.readline()
            if not line:
                break
                
            line = line.decode('utf-8').strip()
            if line:
                logger.info(f"Proxy output: {line}")
                
                # Parse the request line
                request_data = parse_request_line(line)
                if request_data:
                    proxy_state['requests_count'] += 1
                    emit_request(request_data)
                    emit_proxy_state()
                    
        except Exception as e:
            logger.error(f"Error monitoring proxy: {e}")
            break
    
    logger.info("Proxy monitoring stopped")

@app.route('/')
def index():
    """Serve the main UI"""
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

@app.route('/api/proxy/state')
def get_proxy_state():
    """Get current proxy state"""
    return jsonify(proxy_state)

@app.route('/api/proxy/start', methods=['POST'])
def start_proxy():
    """Start the proxy"""
    global proxy_process, proxy_thread, proxy_state
    
    if proxy_state['running']:
        return jsonify({'error': 'Proxy is already running'}), 400
    
    data = request.json or {}
    port = data.get('port', 4545)
    mode = data.get('mode', 'minimal')
    
    try:
        # Build command based on mode
        cmd = [os.path.join(WORK_DIR, 'proxy.sh'), 'live', '--port', str(port)]
        if mode == 'verbose':
            cmd.append('--verbose')
        
        # Start proxy process
        proxy_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
        
        # Update state
        proxy_state['running'] = True
        proxy_state['port'] = port
        proxy_state['mode'] = mode
        proxy_state['start_time'] = datetime.now().isoformat()
        proxy_state['requests_count'] = 0
        
        # Start monitoring thread
        proxy_thread = threading.Thread(target=monitor_proxy_output, daemon=True)
        proxy_thread.start()
        
        emit_proxy_state()
        return jsonify({'status': 'started', 'port': port})
        
    except Exception as e:
        logger.error(f"Error starting proxy: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy/stop', methods=['POST'])
def stop_proxy():
    """Stop the proxy"""
    global proxy_process, proxy_state
    
    if not proxy_state['running']:
        return jsonify({'error': 'Proxy is not running'}), 400
    
    try:
        if proxy_process:
            proxy_process.terminate()
            proxy_process.wait(timeout=5)
            proxy_process = None
        
        # Also run the stop script to ensure system proxy is restored
        subprocess.run([os.path.join(WORK_DIR, 'proxy.sh'), 'stop'], check=True)
        
        proxy_state['running'] = False
        proxy_state['start_time'] = None
        
        emit_proxy_state()
        return jsonify({'status': 'stopped'})
        
    except Exception as e:
        logger.error(f"Error stopping proxy: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/blacklist', methods=['GET'])
def get_blacklist():
    """Get domain blacklist"""
    content = read_config_file('domain_blacklist.txt')
    domains = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
    return jsonify({'domains': domains})

@app.route('/api/config/blacklist', methods=['POST'])
def update_blacklist():
    """Update domain blacklist"""
    data = request.json or {}
    domains = data.get('domains', [])
    
    content = '\n'.join(domains)
    write_config_file('domain_blacklist.txt', content)
    
    return jsonify({'status': 'updated', 'domains': domains})

@app.route('/api/config/interceptor', methods=['GET'])
def get_interceptor_config():
    """Get interceptor configuration"""
    try:
        filepath = os.path.join(WORK_DIR, 'interceptor.config.yaml')
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                config = yaml.safe_load(f) or {}
            return jsonify({'config': config})
        return jsonify({'config': {}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/interceptor', methods=['POST'])
def update_interceptor_config():
    """Update interceptor configuration"""
    try:
        data = request.json or {}
        config = data.get('config', {})
        
        filepath = os.path.join(WORK_DIR, 'interceptor.config.yaml')
        with open(filepath, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return jsonify({'status': 'updated', 'config': config})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """Clear log files"""
    try:
        logs_dir = os.path.join(WORK_DIR, 'logs')
        if os.path.exists(logs_dir):
            for file in os.listdir(logs_dir):
                if file.endswith('.txt') or file.endswith('.log'):
                    os.remove(os.path.join(logs_dir, file))
        
        return jsonify({'status': 'cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('proxy_state', proxy_state)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

def cleanup():
    """Clean up resources on exit"""
    global proxy_process
    
    if proxy_process:
        logger.info("Stopping proxy process...")
        proxy_process.terminate()
        proxy_process.wait()
        
        # Restore system proxy settings
        subprocess.run([os.path.join(WORK_DIR, 'proxy.sh'), 'restore'], check=False)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    cleanup()
    sys.exit(0)

if __name__ == '__main__':
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create logs directory
    os.makedirs(os.path.join(WORK_DIR, 'logs'), exist_ok=True)
    
    # Create templates directory if it doesn't exist
    os.makedirs(os.path.join(WORK_DIR, 'templates'), exist_ok=True)
    
    # Create static directory if it doesn't exist
    os.makedirs(os.path.join(WORK_DIR, 'static'), exist_ok=True)
    
    try:
        print(f"\n[+] Starting Proxy UI Server on http://localhost:5678")
        print(f"[+] Press Ctrl+C to stop\n")
        socketio.run(app, host='0.0.0.0', port=5678, debug=False)
    finally:
        cleanup()