import mitmproxy.http
from mitmproxy import ctx
import os
import datetime
import sys
import re
import json

class UrlOnly:
    def __init__(self):
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Use a single master log file
        self.log_file = "logs/url_log.txt"
        
        # Load domain blacklist
        self.blacklisted_domains = []
        self.load_blacklist()
        
        # Log the start of the session
        with open(self.log_file, "a") as f:
            f.write(f"\n=== Proxy Session Started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
            if self.blacklisted_domains:
                f.write(f"Blacklisted domains: {', '.join(self.blacklisted_domains)}\n\n")
        
        # Print a message to indicate the log file location
        print(f"\n[+] URL logs are being saved to: {self.log_file}")
        print(f"[+] Showing full URLs without truncation")
        print(f"[+] POST requests will show response data")
        
        # Print blacklisted domains
        if self.blacklisted_domains:
            print(f"[+] Ignoring {len(self.blacklisted_domains)} blacklisted domains")
        else:
            print(f"[+] No domains blacklisted. Add domains to domain_blacklist.txt to ignore them.")
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
        
        # Create a custom formatted message with the full URL
        if app_info:
            full_message = f"[{timestamp}] {method} {url} [{app_info}]"
        else:
            full_message = f"[{timestamp}] {method} {url}"
            
        # Print directly to stdout to bypass mitmproxy's formatting
        print(full_message, flush=True)
        
        # Write to log file
        with open(self.log_file, "a") as f:
            f.write(full_message + "\n")
    
    def is_blacklisted(self, host):
        """Check if a host matches any blacklisted domain"""
        for domain in self.blacklisted_domains:
            # Check for exact match or subdomain match
            if host == domain or host.endswith('.' + domain):
                return True
        return False
    
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
addons = [UrlOnly()]
