import mitmproxy.http
from mitmproxy import ctx
import os
import datetime
import sys
import re
import json
import yaml

class UrlInterceptor:
    def __init__(self):
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Use a single master log file
        self.log_file = "logs/url_log.txt"
        
        # Load domain blacklist
        self.blacklisted_domains = []
        self.load_blacklist()
        
        # Load interceptor configuration
        self.interceptor_config = {}
        self.load_interceptor_config()
        
        # Log the start of the session
        with open(self.log_file, "a") as f:
            f.write(f"\n=== Proxy Session Started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
            if self.blacklisted_domains:
                f.write(f"Blacklisted domains: {', '.join(self.blacklisted_domains)}\n")
            if self.interceptor_config:
                f.write(f"Intercepting {len(self.interceptor_config)} URL patterns\n")
            f.write("\n")
        
        # Print startup info
        print(f"\n[+] URL logs are being saved to: {self.log_file}")
        print(f"[+] Showing full URLs without truncation")
        print(f"[+] POST requests will show response data")
        
        if self.blacklisted_domains:
            print(f"[+] Ignoring {len(self.blacklisted_domains)} blacklisted domains")
        
        if self.interceptor_config:
            print(f"[+] Intercepting {len(self.interceptor_config)} URL patterns")
            for url in self.interceptor_config:
                print(f"    - {url}")
        
        print("")
    
    def load_blacklist(self):
        """Load the domain blacklist from domain_blacklist.txt"""
        blacklist_file = "domain_blacklist.txt"
        
        if os.path.exists(blacklist_file):
            with open(blacklist_file, "r") as f:
                for line in f:
                    # Remove comments and whitespace
                    line = line.split('#')[0].strip()
                    if line:  # Skip empty lines
                        self.blacklisted_domains.append(line)
    
    def load_interceptor_config(self):
        """Load the interceptor configuration from YAML file"""
        config_file = "interceptor.config.yaml"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    self.interceptor_config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[!] Error loading interceptor config: {str(e)}")
    
    def is_blacklisted(self, host):
        """Check if a host matches any blacklisted domain"""
        for domain in self.blacklisted_domains:
            # Check for exact match or subdomain match
            if host == domain or host.endswith('.' + domain):
                return True
        return False
    
    def should_intercept(self, flow):
        """Check if the request should be intercepted"""
        url = flow.request.pretty_url
        host = flow.request.host
        path = flow.request.path
        
        # Check exact URL match first (without protocol)
        url_without_protocol = url.split('://', 1)[1] if '://' in url else url
        
        if url_without_protocol in self.interceptor_config:
            return url_without_protocol
        
        # Check host match
        if host in self.interceptor_config:
            return host
        
        # Check for host + path partial matches
        for pattern in self.interceptor_config:
            # Skip patterns that are just hostnames (already checked)
            if '/' not in pattern:
                continue
                
            # Check if pattern is contained in URL
            if pattern in url_without_protocol:
                return pattern
        
        return None
    
    def apply_intercept(self, flow: mitmproxy.http.HTTPFlow, pattern):
        """Apply interception rules to a flow"""
        config = self.interceptor_config[pattern]
        
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
    
    def request(self, flow: mitmproxy.http.HTTPFlow):
        # Get the URL and method
        url = flow.request.pretty_url
        method = flow.request.method
        
        # Check if the domain is blacklisted
        host = flow.request.host
        if self.is_blacklisted(host):
            return
        
        # Get the User-Agent to identify the app
        user_agent = flow.request.headers.get("User-Agent", "")
        
        # Extract app info from User-Agent if possible
        app_info = ""
        if "Safari" in user_agent:
            app_info = "Safari"
        elif "Chrome" in user_agent:
            app_info = "Chrome"
        elif "Firefox" in user_agent:
            app_info = "Firefox"
        
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
            if app_info:
                full_message = f"[{timestamp}] {method} {url} [{app_info}]"
            else:
                full_message = f"[{timestamp}] {method} {url}"
                
            # Print directly to stdout
            print(full_message, flush=True)
            
            # Write to log file
            with open(self.log_file, "a") as f:
                f.write(full_message + "\n")
    
    def response(self, flow: mitmproxy.http.HTTPFlow):
        """Handle responses, especially for POST requests"""
        # Only process POST responses that aren't blacklisted
        if flow.request.method != "POST":
            return
            
        host = flow.request.host
        if self.is_blacklisted(host):
            return
        
        # Get response details
        status_code = flow.response.status_code
        content_type = flow.response.headers.get("Content-Type", "")
        
        # Format response info
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        response_msg = f"[{timestamp}] └─ Response: {status_code}"
        
        # Try to get response body
        try:
            response_body = flow.response.text
            
            # Limit response body display
            if len(response_body) > 500:
                response_body = response_body[:500] + "... (truncated)"
            
            # Try to format JSON responses
            if "application/json" in content_type:
                try:
                    json_data = json.loads(flow.response.text)
                    response_body = json.dumps(json_data, indent=2)[:500]
                except:
                    pass
            
            # Display response
            print(f"{response_msg} {content_type}", flush=True)
            if response_body.strip():
                # Indent response body
                indented_body = "\n".join("    " + line for line in response_body.split("\n"))
                print(indented_body, flush=True)
                print("", flush=True)  # Empty line for readability
                
                # Log to file
                with open(self.log_file, "a") as f:
                    f.write(f"{response_msg} {content_type}\n")
                    f.write(indented_body + "\n\n")
            else:
                print("    (empty response)", flush=True)
                print("", flush=True)
                
                with open(self.log_file, "a") as f:
                    f.write(f"{response_msg} {content_type}\n    (empty response)\n\n")
                    
        except Exception as e:
            error_msg = f"    Error reading response: {str(e)}"
            print(error_msg, flush=True)
            print("", flush=True)
            
            with open(self.log_file, "a") as f:
                f.write(f"{response_msg}\n{error_msg}\n\n")

# Configure mitmproxy to use our addon
addons = [UrlInterceptor()]