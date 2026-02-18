#!/usr/bin/env python3
"""Google Ads OAuth Refresh Token Generator.

Generates an OAuth2 refresh token for the Google Ads API.
This is a one-time setup script.

Usage:
    python scripts/google_ads_auth.py
    python scripts/google_ads_auth.py --client-id=XXX --client-secret=YYY

The script will:
1. Open a browser for Google OAuth consent
2. Wait for you to paste the authorization code
3. Exchange the code for a refresh token
4. Print the refresh token for .env configuration

Prerequisites:
    - Google Cloud Console project with Google Ads API enabled
    - OAuth 2.0 Client ID (Desktop app type)
    - pip install requests (already in project dependencies)
"""

import argparse
import os
import sys
import webbrowser

try:
    import requests
except ImportError:
    print("Error: 'requests' package is required. Run: pip install requests")
    sys.exit(1)

OAUTH_SCOPE = "https://www.googleapis.com/auth/adwords"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
# OOB redirect for manual copy-paste flow (simplest for CLI scripts)
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


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

    auth_url = get_authorization_url(client_id)

    print(f"\n1. Opening browser for authorization...")
    print(f"   URL: {auth_url}\n")

    try:
        webbrowser.open(auth_url)
    except Exception:
        print("   (Could not open browser automatically. Please open the URL manually.)")

    print("2. Sign in with your Google account and authorize the application.")
    print("3. Copy the authorization code and paste it below.\n")

    auth_code = input("Authorization code: ").strip()

    if not auth_code:
        print("Error: No authorization code provided.")
        sys.exit(1)

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
        print("\nError: No refresh token in response. Try adding 'prompt=consent' or revoking previous access.")
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
