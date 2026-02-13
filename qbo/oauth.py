#!/usr/bin/env python3
"""
QBO OAuth2 Authorization Flow

Starts a local server, opens the Intuit authorization page in your browser,
and exchanges the callback code for access + refresh tokens.

Usage:
    python qbo/oauth.py              # Re-authorize default company
    python qbo/oauth.py --sandbox    # Use sandbox environment

Requires QBO_CLIENT_ID and QBO_CLIENT_SECRET in config/.env
"""

import json
import os
import secrets
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / "config" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

CLIENT_ID = os.getenv("QBO_CLIENT_ID")
CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET")
TOKEN_ENDPOINT = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
AUTH_ENDPOINT = "https://appcenter.intuit.com/connect/oauth2"
REDIRECT_URI = "http://localhost:8080/callback"
TOKENS_DIR = Path(__file__).parent.parent / "config" / "tokens"

SCOPES = "com.intuit.quickbooks.accounting"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth callback from Intuit."""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)

        if "error" in params:
            error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h2>Authorization failed: {error}</h2>".encode())
            self.server.auth_result = {"error": error}
            return

        code = params.get("code", [None])[0]
        realm_id = params.get("realmId", [None])[0]
        state = params.get("state", [None])[0]

        if not code or not realm_id:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Missing code or realmId</h2>")
            self.server.auth_result = {"error": "missing params"}
            return

        # Verify state
        if state != self.server.expected_state:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Invalid state parameter</h2>")
            self.server.auth_result = {"error": "state mismatch"}
            return

        # Exchange code for tokens
        try:
            response = requests.post(
                TOKEN_ENDPOINT,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                },
                auth=(CLIENT_ID, CLIENT_SECRET),
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")

            tokens = response.json()
            tokens["realmId"] = realm_id

            # Save tokens
            TOKENS_DIR.mkdir(parents=True, exist_ok=True)

            # Save as default
            default_path = TOKENS_DIR / "default.json"
            with open(default_path, "w") as f:
                json.dump(tokens, f, indent=2)

            # Also save by realm ID
            realm_path = TOKENS_DIR / f"{realm_id}.json"
            with open(realm_path, "w") as f:
                json.dump(tokens, f, indent=2)

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<h2>Connected to QBO company {realm_id}</h2>"
                f"<p>Tokens saved. You can close this tab.</p>".encode()
            )
            self.server.auth_result = {"ok": True, "realm_id": realm_id}

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h2>Error: {e}</h2>".encode())
            self.server.auth_result = {"error": str(e)}

    def log_message(self, format, *args):
        # Suppress default request logging
        pass


def run_oauth_flow(sandbox=False):
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: QBO_CLIENT_ID and QBO_CLIENT_SECRET must be set in config/.env")
        sys.exit(1)

    state = secrets.token_urlsafe(16)

    auth_params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }

    auth_url = f"{AUTH_ENDPOINT}?{urlencode(auth_params)}"

    server = HTTPServer(("localhost", 8080), OAuthCallbackHandler)
    server.expected_state = state
    server.auth_result = None

    print(f"Opening browser for QBO authorization...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for callback on http://localhost:8080/callback ...")

    while server.auth_result is None:
        server.handle_request()

    server.server_close()

    result = server.auth_result
    if result.get("ok"):
        print(f"\nSuccess! Connected to QBO company {result['realm_id']}")
        print(f"Tokens saved to {TOKENS_DIR}/default.json")
    else:
        print(f"\nFailed: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    sandbox = "--sandbox" in sys.argv
    run_oauth_flow(sandbox=sandbox)
