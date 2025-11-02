#!/usr/bin/env python3
"""
Whoop OAuth Re-authentication Script

This script helps you re-authenticate with the Whoop API when your access token expires.
It will guide you through the OAuth flow and save your new tokens.
"""

import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse

import httpx
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
env_path = Path(__file__).parent.parent / "config" / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Whoop OAuth configuration
CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")
TOKEN_FILE = Path(__file__).parent.parent / "config" / "tokens.json"

WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

# Required scopes
SCOPES = "read:recovery read:cycles read:workout read:sleep read:profile read:body_measurement offline"


def generate_authorization_url():
    """Generate OAuth authorization URL."""
    state = secrets.token_urlsafe(32)
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state
    }
    
    auth_url = f"{WHOOP_AUTH_URL}?{urlencode(params)}"
    return auth_url, state


def exchange_code_for_tokens(authorization_code: str):
    """Exchange authorization code for access and refresh tokens."""
    try:
        response = httpx.post(WHOOP_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        })
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error exchanging code for tokens: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def save_tokens(token_data: dict):
    """Save tokens to file."""
    from datetime import datetime
    
    tokens = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "updated_at": datetime.now().isoformat()
    }
    
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    
    # Secure the token file
    os.chmod(TOKEN_FILE, 0o600)
    print(f"✅ Tokens saved to {TOKEN_FILE}")


def main():
    """Main authentication flow."""
    print("🔐 Whoop OAuth Re-authentication")
    print("=" * 50)
    
    # Validate configuration
    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        print("❌ Missing OAuth credentials in environment variables")
        print("Required: WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET, WHOOP_REDIRECT_URI")
        return 1
    
    # Generate authorization URL
    print("\n📝 Step 1: Generating authorization URL...")
    auth_url, state = generate_authorization_url()
    
    print(f"\n🔗 Step 2: Open this URL in your browser:")
    print("=" * 50)
    print(auth_url)
    print("=" * 50)
    
    print(f"\n⚠️  Important: Make sure the redirect URI matches: {REDIRECT_URI}")
    print("\n📋 Step 3: After authorizing, you'll be redirected to the callback URL.")
    print("   Copy the FULL callback URL (including all parameters) and paste it below.")
    print("\n💡 Tip: The URL will look like:")
    print(f"   {REDIRECT_URI}?code=AUTHORIZATION_CODE&state=STATE_VALUE")
    print("\n" + "-" * 50)
    
    # Get callback URL from user
    callback_url = input("\n📥 Paste the callback URL here: ").strip()
    
    if not callback_url:
        print("❌ No URL provided")
        return 1
    
    # Parse callback URL
    try:
        parsed = urlparse(callback_url)
        query_params = parse_qs(parsed.query)
        
        # Check for errors
        if "error" in query_params:
            error = query_params["error"][0]
            error_desc = query_params.get("error_description", [""])[0]
            print(f"\n❌ OAuth Error: {error}")
            if error_desc:
                print(f"   Description: {error_desc}")
            return 1
        
        # Extract authorization code
        if "code" not in query_params:
            print("❌ No authorization code found in callback URL")
            return 1
        
        auth_code = query_params["code"][0]
        
        # Verify state (optional but recommended)
        if "state" in query_params:
            callback_state = query_params["state"][0]
            if callback_state != state:
                print("⚠️  Warning: State mismatch (possible CSRF attack)")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != "y":
                    return 1
        
    except Exception as e:
        print(f"❌ Error parsing callback URL: {e}")
        return 1
    
    # Exchange code for tokens
    print("\n🔄 Step 4: Exchanging authorization code for tokens...")
    token_data = exchange_code_for_tokens(auth_code)
    
    if not token_data:
        print("❌ Failed to get tokens")
        return 1
    
    # Save tokens
    print("\n💾 Step 5: Saving tokens...")
    save_tokens(token_data)
    
    # Verify tokens
    print("\n✅ Step 6: Verifying tokens...")
    access_token = token_data["access_token"]
    try:
        response = httpx.get(
            "https://api.prod.whoop.com/developer/v2/user/profile/basic",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code == 200:
            profile = response.json()
            print(f"✅ Successfully authenticated!")
            print(f"   User: {profile.get('first_name', '')} {profile.get('last_name', '')}")
            print(f"   Email: {profile.get('email', '')}")
        else:
            print(f"⚠️  Token saved but verification failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"⚠️  Token saved but verification failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Authentication complete!")
    print(f"   Tokens saved to: {TOKEN_FILE}")
    print("   You can now use the Whoop MCP server.")
    print("=" * 50)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

