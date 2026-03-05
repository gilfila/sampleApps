#!/usr/bin/env python3
"""
Run the PKCE flow and obtain a refresh token via a local callback server.

Prerequisites:
  - In .env: WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET, WORKDAY_TOKEN_URL (e.g. https://auth.api.workday.com/v1/token).
  - In your Workday API Client registration, add this redirect URI: http://localhost:8765/callback

Usage:
  python generate_refresh_token.py

Then:
  1. Open the printed URL in your browser and sign in to Workday.
  2. You will be redirected to localhost; the script will exchange the code and print the refresh token.
  3. Add WORKDAY_REFRESH_TOKEN=... to your .env file.
"""

import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

_load_dir = os.path.dirname(os.path.abspath(__file__))
if _load_dir not in sys.path:
    sys.path.insert(0, _load_dir)

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(_load_dir, ".env"))

# Use local callback for this script so we can capture the code
LOCAL_REDIRECT_URI = "http://localhost:8765/callback"
LOCAL_PORT = 8765
PKCE_VERIFIER_FILE = os.path.join(_load_dir, ".workday_pkce_verifier")

# Result stored by the request handler for the main thread to read
_exchange_result: dict | None = None
_server_ref: HTTPServer | None = None


CALLBACK_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Workday OAuth</title></head><body>
<script>
(function() {
  var hash = window.location.hash.slice(1);
  var params = new URLSearchParams(hash);
  var code = params.get('code');
  if (code) {
    window.location.href = '/exchange?code=' + encodeURIComponent(code);
  } else {
    document.body.innerHTML = '<p>No authorization code in URL. Check the redirect from Workday.</p>';
  }
})();
</script>
<p>Completing sign-in...</p>
</body></html>
"""


def success_html(refresh_token: str, add_to_env: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Success</title></head><body>
<h2>Refresh token obtained</h2>
<p>Add this line to your <code>.env</code> file:</p>
<pre style="background:#eee;padding:1em;overflow:auto;">{add_to_env}</pre>
<p>Then restart the MCP server or run the tool again.</p>
<p>You can close this tab.</p>
</body></html>
"""


def error_html(message: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Error</title></head><body>
<h2>Token exchange failed</h2>
<pre style="color:red;">{message}</pre>
<p>Check .env (WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET, WORKDAY_REDIRECT_URI, WORKDAY_TOKEN_URL) and that the redirect URI is registered for your Workday API client.</p>
</body></html>
"""


class OAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def do_GET(self):
        global _exchange_result, _server_ref
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/callback":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(CALLBACK_HTML.encode("utf-8"))
            return

        if path == "/exchange" and "code" in query:
            code = query["code"][0].strip()
            code_verifier = None
            if os.path.isfile(PKCE_VERIFIER_FILE):
                try:
                    with open(PKCE_VERIFIER_FILE) as f:
                        code_verifier = f.read().strip()
                    os.remove(PKCE_VERIFIER_FILE)
                except OSError:
                    pass

            from workday_auth import exchange_authorization_code

            try:
                data = exchange_authorization_code(
                    code,
                    redirect_uri=LOCAL_REDIRECT_URI,
                    code_verifier=code_verifier,
                )
                refresh_token = data.get("refresh_token", "")
                _exchange_result = data
                line = f"WORKDAY_REFRESH_TOKEN_NONEXPIRE={refresh_token}" if refresh_token else ""
                body = success_html(refresh_token, line)
            except Exception as e:
                _exchange_result = {"error": str(e)}
                body = error_html(str(e))

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

            if _server_ref:
                _server_ref.shutdown()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        self.do_GET()


def main() -> None:
    global _server_ref

    os.environ["WORKDAY_REDIRECT_URI"] = LOCAL_REDIRECT_URI

    from workday_auth import get_workday_authorize_url_pkce

    try:
        url, verifier = get_workday_authorize_url_pkce(redirect_uri_override=LOCAL_REDIRECT_URI)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(PKCE_VERIFIER_FILE, "w") as f:
            f.write(verifier)
    except OSError as e:
        print(f"Warning: could not save code_verifier: {e}", file=sys.stderr)

    print("Ensure this redirect URI is registered for your Workday API client:")
    print(f"  {LOCAL_REDIRECT_URI}")
    print()
    print("Open this URL in your browser, sign in, and you will be redirected back here:")
    print()
    print(url)
    print()
    print("Waiting for callback...")

    try:
        _server_ref = HTTPServer(("", LOCAL_PORT), OAuthHandler)
        _server_ref.handle_request()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(1)

    if _exchange_result and "error" in _exchange_result:
        print(f"Exchange failed: {_exchange_result['error']}", file=sys.stderr)
        sys.exit(1)
    if _exchange_result and _exchange_result.get("refresh_token"):
        print()
        print("Add this to your .env file:")
        print(f"WORKDAY_REFRESH_TOKEN_NONEXPIRE={_exchange_result['refresh_token']}")
        print()


if __name__ == "__main__":
    main()
