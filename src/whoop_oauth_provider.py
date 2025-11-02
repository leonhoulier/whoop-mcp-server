#!/usr/bin/env python3
"""
Whoop OAuth Provider for MCP Server

This module implements the OAuthAuthorizationServerProvider interface for Whoop API integration.
It handles per-session OAuth tokens and integrates with the existing Whoop OAuth flow.
"""

import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlencode

from mcp.server.auth.provider import (
    OAuthAuthorizationServerProvider,
    AuthorizationCode,
    RefreshToken,
    AccessToken,
    AuthorizationParams,
    AuthorizeError,
    TokenError,
    RegistrationError,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyUrl

logger = logging.getLogger("whoop-oauth-provider")

# Whoop OAuth configuration
WHOOP_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
WHOOP_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET") 
WHOOP_REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")
WHOOP_EMAIL = os.getenv("WHOOP_EMAIL")
WHOOP_PASSWORD = os.getenv("WHOOP_PASSWORD")

# Storage paths
STORAGE_DIR = Path(__file__).parent.parent / "storage"
CLIENTS_FILE = STORAGE_DIR / "oauth_clients.json"
TOKENS_FILE = STORAGE_DIR / "oauth_tokens.json"
AUTH_CODES_FILE = STORAGE_DIR / "oauth_auth_codes.json"


class WhoopOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    """
    OAuth provider for Whoop API integration with per-session token management.
    
    This provider:
    1. Stores client registrations (in-memory with file persistence)
    2. Handles authorization code flow with PKCE
    3. Issues per-session tokens linked to Whoop user tokens
    4. Manages token lifecycle (access, refresh, revocation)
    """
    
    def __init__(self):
        self._clients: Dict[str, OAuthClientInformationFull] = {}
        self._tokens: Dict[str, AccessToken] = {}
        self._auth_codes: Dict[str, AuthorizationCode] = {}
        self._whoop_tokens: Dict[str, Dict[str, Any]] = {}  # session_id -> whoop_token_data
        
        # Ensure storage directory exists
        STORAGE_DIR.mkdir(exist_ok=True)
        
        # Load persisted data
        self._load_clients()
        self._load_tokens()
        self._load_auth_codes()
        
        # Load existing Whoop tokens if available
        self._load_whoop_tokens()
    
    def _load_clients(self):
        """Load client registrations from file."""
        if CLIENTS_FILE.exists():
            try:
                with open(CLIENTS_FILE, "r") as f:
                    data = json.load(f)
                    for client_id, client_data in data.items():
                        self._clients[client_id] = OAuthClientInformationFull(**client_data)
                logger.info(f"Loaded {len(self._clients)} clients from storage")
            except Exception as e:
                logger.error(f"Failed to load clients: {e}")
    
    def _save_clients(self):
        """Save client registrations to file."""
        try:
            # Convert AnyUrl objects to strings for JSON serialization
            data = {}
            for cid, client in self._clients.items():
                client_dict = client.model_dump()
                # Convert AnyUrl objects to strings
                for key, value in client_dict.items():
                    if isinstance(value, AnyUrl):
                        client_dict[key] = str(value)
                    elif isinstance(value, list) and value and isinstance(value[0], AnyUrl):
                        client_dict[key] = [str(v) for v in value]
                data[cid] = client_dict
            with open(CLIENTS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save clients: {e}")
    
    def _load_tokens(self):
        """Load access tokens from file."""
        if TOKENS_FILE.exists():
            try:
                with open(TOKENS_FILE, "r") as f:
                    data = json.load(f)
                    for token, token_data in data.items():
                        self._tokens[token] = AccessToken(**token_data)
                logger.info(f"Loaded {len(self._tokens)} tokens from storage")
            except Exception as e:
                logger.error(f"Failed to load tokens: {e}")
    
    def _save_tokens(self):
        """Save access tokens to file."""
        try:
            data = {token: access_token.model_dump() for token, access_token in self._tokens.items()}
            with open(TOKENS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
    
    def _load_auth_codes(self):
        """Load authorization codes from file."""
        if AUTH_CODES_FILE.exists():
            try:
                with open(AUTH_CODES_FILE, "r") as f:
                    data = json.load(f)
                    for code, code_data in data.items():
                        # Convert string URLs back to AnyUrl
                        if 'redirect_uri' in code_data:
                            code_data['redirect_uri'] = AnyUrl(code_data['redirect_uri'])
                        self._auth_codes[code] = AuthorizationCode(**code_data)
                logger.info(f"Loaded {len(self._auth_codes)} auth codes from storage")
            except Exception as e:
                logger.error(f"Failed to load auth codes: {e}")
    
    def _save_auth_codes(self):
        """Save authorization codes to file."""
        try:
            data = {}
            for code, auth_code in self._auth_codes.items():
                auth_dict = auth_code.model_dump()
                # Convert AnyUrl to string
                if 'redirect_uri' in auth_dict and isinstance(auth_dict['redirect_uri'], AnyUrl):
                    auth_dict['redirect_uri'] = str(auth_dict['redirect_uri'])
                data[code] = auth_dict
            with open(AUTH_CODES_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save auth codes: {e}")
    
    def _load_whoop_tokens(self):
        """Load existing Whoop tokens if available."""
        tokens_path = Path(__file__).parent.parent / "config" / "tokens.json"
        if tokens_path.exists():
            try:
                with open(tokens_path, "r") as f:
                    whoop_data = json.load(f)
                    # Create a default session for existing tokens
                    if whoop_data.get("access_token"):
                        session_id = "default_session"
                        self._whoop_tokens[session_id] = whoop_data
                        logger.info("Loaded existing Whoop tokens for default session")
            except Exception as e:
                logger.error(f"Failed to load Whoop tokens: {e}")
    
    async def get_client(self, client_id: str) -> Optional[OAuthClientInformationFull]:
        """Get client information by client ID."""
        return self._clients.get(client_id)
    
    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Register a new client."""
        # Validate client metadata
        if not client_info.redirect_uris:
            raise RegistrationError("invalid_redirect_uri", "At least one redirect URI is required")
        
        # Generate client ID and secret
        client_info.client_id = secrets.token_urlsafe(32)
        client_info.client_secret = secrets.token_urlsafe(32)
        client_info.client_id_issued_at = int(time.time())
        
        # Store client
        self._clients[client_info.client_id] = client_info
        self._save_clients()
        
        logger.info(f"Registered new client: {client_info.client_id}")
    
    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """Handle authorization request and redirect to Whoop OAuth."""
        # Generate authorization code
        auth_code = secrets.token_urlsafe(32)
        
        # Store authorization code
        authorization_code = AuthorizationCode(
            code=auth_code,
            scopes=params.scopes or [],
            expires_at=time.time() + 600,  # 10 minutes
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource
        )
        
        self._auth_codes[auth_code] = authorization_code
        self._save_auth_codes()
        
        # Build Whoop OAuth URL with CORRECT endpoint
        whoop_params = {
            "response_type": "code",
            "client_id": WHOOP_CLIENT_ID,
            "redirect_uri": WHOOP_REDIRECT_URI,
            "scope": "read:recovery read:workout read:profile",
            "state": params.state or secrets.token_urlsafe(16)
        }
        
        # Use the CORRECT Whoop OAuth endpoint: /oauth/oauth2/auth (not authorize)
        whoop_auth_url = f"https://api.prod.whoop.com/oauth/oauth2/auth?{urlencode(whoop_params)}"
        
        logger.info(f"Generated auth code {auth_code} for client {client.client_id}")
        logger.info(f"Redirecting to Whoop OAuth: {whoop_auth_url}")
        
        return whoop_auth_url
    
    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> Optional[AuthorizationCode]:
        """Load authorization code by code string."""
        code = self._auth_codes.get(authorization_code)
        if not code:
            return None
        
        # Check if expired
        if time.time() > code.expires_at:
            del self._auth_codes[authorization_code]
            self._save_auth_codes()
            return None
        
        return code
    
    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        """Exchange authorization code for access token."""
        # Remove used authorization code
        if authorization_code.code in self._auth_codes:
            del self._auth_codes[authorization_code.code]
            self._save_auth_codes()
        
        # For now, use existing Whoop tokens or create a session-specific token
        # In a real implementation, you'd exchange the Whoop auth code for a token here
        session_id = f"session_{secrets.token_hex(8)}"
        
        # Get or create Whoop tokens for this session
        whoop_tokens = self._whoop_tokens.get("default_session", {})
        if not whoop_tokens:
            # If no existing tokens, we'd need to implement the Whoop OAuth exchange
            # For now, raise an error
            raise TokenError("invalid_grant", "No Whoop tokens available for session")
        
        # Create session-specific Whoop tokens
        self._whoop_tokens[session_id] = whoop_tokens.copy()
        
        # Generate MCP access token
        access_token = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + 3600  # 1 hour
        
        mcp_access_token = AccessToken(
            token=access_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=expires_at,
            resource=authorization_code.resource
        )
        
        # Store the access token
        self._tokens[access_token] = mcp_access_token
        self._save_tokens()
        
        # Generate refresh token
        refresh_token = secrets.token_urlsafe(32)
        
        mcp_refresh_token = RefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=expires_at + 86400  # 24 hours
        )
        
        logger.info(f"Issued access token {access_token} for client {client.client_id}, session {session_id}")
        
        return OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(authorization_code.scopes) if authorization_code.scopes else None,
            refresh_token=refresh_token
        )
    
    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> Optional[RefreshToken]:
        """Load refresh token by token string."""
        # For simplicity, we'll store refresh tokens in the same tokens dict
        # In a real implementation, you'd have a separate refresh token storage
        return None  # Simplified for now
    
    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        """Exchange refresh token for new access token."""
        # For now, just issue a new access token
        # In a real implementation, you'd validate the refresh token and potentially
        # refresh the underlying Whoop tokens
        
        access_token = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + 3600  # 1 hour
        
        mcp_access_token = AccessToken(
            token=access_token,
            client_id=client.client_id,
            scopes=scopes,
            expires_at=expires_at
        )
        
        self._tokens[access_token] = mcp_access_token
        self._save_tokens()
        
        logger.info(f"Issued new access token {access_token} for client {client.client_id}")
        
        return OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(scopes) if scopes else None
        )
    
    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        """Load access token by token string."""
        access_token = self._tokens.get(token)
        if not access_token:
            return None
        
        # Check if expired
        if access_token.expires_at and time.time() > access_token.expires_at:
            del self._tokens[token]
            self._save_tokens()
            return None
        
        return access_token
    
    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        """Revoke a token."""
        if isinstance(token, AccessToken):
            if token.token in self._tokens:
                del self._tokens[token.token]
                self._save_tokens()
                logger.info(f"Revoked access token {token.token}")
        
        # For refresh tokens, we'd need separate storage
        logger.info(f"Token revocation requested for {type(token).__name__}")
    
    def get_whoop_tokens_for_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get Whoop tokens for a specific session."""
        return self._whoop_tokens.get(session_id)
    
    def create_session_for_token(self, access_token: str) -> str:
        """Create a new session for an access token."""
        session_id = f"session_{secrets.token_hex(8)}"
        
        # Copy default Whoop tokens to new session
        default_tokens = self._whoop_tokens.get("default_session", {})
        if default_tokens:
            self._whoop_tokens[session_id] = default_tokens.copy()
        
        logger.info(f"Created session {session_id} for access token {access_token}")
        return session_id


# Global provider instance
provider = WhoopOAuthProvider()
