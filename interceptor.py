import mitmproxy.http
from mitmproxy import ctx
import os
import datetime
import sys
import re
import json
import yaml

class Interceptor:
    def __init__(self):
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Use a log file for intercepted requests
        self.log_file = "logs/interceptor_log.txt"
        
        # Load the interceptor configuration
        self.config = {}
        self.config_file = "interceptor.config.yaml"
        self.load_config()
        
        # Log the start of the session
        with open(self.log_file, "a") as f:
            f.write(f"\n=== Interceptor Session Started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
            if self.config:
                f.write(f"Loaded {len(self.config)} URL intercept configurations\n\n")
        
        # Print a message to indicate the interceptor is running
        print(f"\n[+] Interceptor is active")
        print(f"[+] Interceptor logs are being saved to: {self.log_file}")
        
        # Print loaded configurations
        if self.config:
            print(f"[+] Intercepting {len(self.config)} URL patterns")
            for url, _ in self.config.items():
                print(f"    - {url}")
        else:
            print(f"[!] No interception rules found. Add rules to {self.config_file}")
        print("")
    
    def load_config(self):
        """Load the interceptor configuration from YAML file"""
        if not os.path.exists(self.config_file):
            print(f"[!] Config file {self.config_file} not found. Creating a template...")
            self.create_template_config()
            return
        
        try:
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            print(f"[+] Loaded configuration from {self.config_file}")
        except Exception as e:
            print(f"[!] Error loading config: {str(e)}")
            self.config = {}
    
    def create_template_config(self):
        """Create a template configuration file"""
        template = {
            "example.com": {
                "status": 200,
                "content": "This is an intercepted response",
                "headers": {
                    "Content-Type": "text/plain",
                    "X-Intercepted": "true"
                }
            },
            "api.example.org/v1/users": {
                "status": 200,
                "content": {"users": [{"id": 1, "name": "Test User"}]},
                "headers": {
                    "Content-Type": "application/json",
                    "X-Intercepted": "true"
                }
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(template, f, default_flow_style=False)
            print(f"[+] Created template configuration file: {self.config_file}")
        except Exception as e:
            print(f"[!] Error creating template config: {str(e)}")
    
    def should_intercept(self, flow):
        """Check if the request should be intercepted"""
        url = flow.request.pretty_url
        host = flow.request.host
        path = flow.request.path
        
        # Check exact URL match first (without protocol)
        url_without_protocol = url.split('://', 1)[1] if '://' in url else url
        
        if url_without_protocol in self.config:
            return url_without_protocol
        
        # Check host match
        if host in self.config:
            return host
        
        # Check for host + path partial matches
        for pattern in self.config:
            # Skip patterns that are just hostnames (already checked)
            if '/' not in pattern:
                continue
                
            # Check if pattern is contained in URL
            if pattern in url_without_protocol:
                return pattern
        
        return None
    
    def request(self, flow: mitmproxy.http.HTTPFlow):
        """Process an HTTP request"""
        # Get the URL and method
        url = flow.request.pretty_url
        method = flow.request.method
        
        # Format the log message with timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Check if we should intercept this request
        pattern = self.should_intercept(flow)
        if pattern:
            # Log the interception
            intercept_msg = f"[{timestamp}] INTERCEPTING {method} {url} -> using rule '{pattern}'"
            print(intercept_msg, flush=True)
            
            # Write to log file
            with open(self.log_file, "a") as f:
                f.write(intercept_msg + "\n")
            
            # Apply the interception
            self.apply_intercept(flow, pattern)
        else:
            # Normal request (not intercepted)
            pass  # Let the request continue normally
    
    def apply_intercept(self, flow: mitmproxy.http.HTTPFlow, pattern):
        """Apply interception rules to a flow"""
        config = self.config[pattern]
        
        # Set the response status code (default to 200 if not specified)
        status_code = config.get("status", 200)
        
        # Set the response content
        content = config.get("content", "")
        
        # Convert content to a string if it's a dict/list (for JSON)
        if isinstance(content, (dict, list)):
            content = json.dumps(content)
        
        # Set headers
        headers = config.get("headers", {})
        
        # Create a response using the correct mitmproxy API
        flow.response = mitmproxy.http.Response.make(
            status_code,
            content.encode() if isinstance(content, str) else content,
            {k: str(v) for k, v in headers.items()}
        )

# Configure mitmproxy to use our addon
addons = [Interceptor()]
