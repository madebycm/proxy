import mitmproxy.http
from mitmproxy import ctx
import os
import datetime
import sys
import re

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

# Configure mitmproxy to use our addon
addons = [UrlOnly()]
