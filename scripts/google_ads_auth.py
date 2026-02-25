#!/usr/bin/env python3
"""Google Ads OAuth Refresh Token Generator.

Generates an OAuth2 refresh token for the Google Ads API.
This is a one-time setup script.

Usage:
    set -a && source .env && set +a && uv run python scripts/google_ads_auth.py

The script will:
1. Start a local HTTP server on port 8085
2. Open a browser for Google OAuth consent
3. Capture the authorization code via redirect
4. Exchange the code for a refresh token
5. Print the refresh token for .env configuration

Prerequisites:
    - Google Cloud Console project with Google Ads API enabled
    - OAuth 2.0 Client ID (Desktop app type)
    - Authorized redirect URI: http://localhost:8085 in Google Cloud Console
    - pip install requests (already in project dependencies)
"""

import argparse
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

try:
    import requests
except ImportError:
    print("Error: 'requests' package is required. Run: pip install requests")
    sys.exit(1)

OAUTH_SCOPE = "https://www.googleapis.com/auth/adwords"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REDIRECT_PORT = 8085
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"

# Global to capture auth code from callback
_auth_code: str | None = None
_auth_error: str | None = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth redirect callback."""

    def do_GET(self):
        global _auth_code, _auth_error
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>OK</h2>"
                b"<p>Authorization code received. You can close this tab.</p>"
                b"</body></html>"
            )
        elif "error" in params:
            _auth_error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h2>Error: {_auth_error}</h2></body></html>".encode()
            )
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress logs


def get_authorization_url(client_id: str) -> str:
    """Build the OAuth authorization URL."""
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": OAUTH_SCOPE,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{AUTH_ENDPOINT}?{query}"


def exchange_code_for_tokens(client_id: str, client_secret: str, auth_code: str) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    resp = requests.post(TOKEN_ENDPOINT, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Google Ads OAuth refresh token")
    parser.add_argument("--client-id", help="OAuth Client ID (or set GOOGLE_ADS_CLIENT_ID env var)")
    parser.add_argument("--client-secret", help="OAuth Client Secret (or set GOOGLE_ADS_CLIENT_SECRET env var)")
    args = parser.parse_args()

    client_id = args.client_id or os.getenv("GOOGLE_ADS_CLIENT_ID", "")
    client_secret = args.client_secret or os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required.")
        print("  Provide via --client-id/--client-secret flags or set env vars:")
        print("  GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET")
        sys.exit(1)

    print("=" * 60)
    print("Google Ads OAuth Refresh Token Generator")
    print("=" * 60)
    print(f"\nRedirect URI: {REDIRECT_URI}")
    print("Make sure this URI is registered in Google Cloud Console")
    print("  -> APIs & Services -> Credentials -> OAuth 2.0 Client ID")
    print("  -> Authorized redirect URIs\n")

    # Start local server to capture callback
    server = HTTPServer(("localhost", REDIRECT_PORT), OAuthCallbackHandler)
    server_thread = threading.Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    auth_url = get_authorization_url(client_id)
    print(f"1. Opening browser for authorization...")
    print(f"   URL: {auth_url}\n")

    try:
        webbrowser.open(auth_url)
    except Exception:
        print("   (Could not open browser. Please open the URL manually.)")

    print("2. Sign in with your Google account and authorize the application.")
    print("   Waiting for redirect callback...\n")

    server_thread.join(timeout=120)
    server.server_close()

    if _auth_error:
        print(f"Error: OAuth error: {_auth_error}")
        sys.exit(1)

    if not _auth_code:
        print("Error: Timed out waiting for authorization (120s).")
        print("Alternatively, paste the authorization code manually:")
        manual_code = input("Authorization code: ").strip()
        if not manual_code:
            sys.exit(1)
        auth_code = manual_code
    else:
        auth_code = _auth_code
        print("Authorization code received!")

    print("\nExchanging code for tokens...")

    try:
        tokens = exchange_code_for_tokens(client_id, client_secret, auth_code)
    except requests.HTTPError as e:
        print(f"\nError: Failed to exchange code: {e}")
        if e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)

    refresh_token = tokens.get("refresh_token")

    if not refresh_token:
        print("\nError: No refresh token in response.")
        print(f"Response: {tokens}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SUCCESS! Add this to your .env file:")
    print("=" * 60)
    print(f"\nGOOGLE_ADS_REFRESH_TOKEN={refresh_token}")
    print(f"\nAlso set USE_MOCK_GOOGLE_ADS=false to enable real API mode.")
    print("=" * 60)


if __name__ == "__main__":
    main()
