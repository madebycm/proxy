import mitmproxy.http
from mitmproxy import ctx

class UrlOnly:
    def request(self, flow: mitmproxy.http.HTTPFlow):
        # Get the URL and method
        url = flow.request.pretty_url
        method = flow.request.method
        
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
        
        # Print only the URL and app info
        if app_info:
            ctx.log.info(f"{method} {url} [{app_info}]")
        else:
            ctx.log.info(f"{method} {url}")

addons = [UrlOnly()]
