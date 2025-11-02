#!/usr/bin/env python3
import logging
import os
import sys
import secrets
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route

CURRENT_DIR = Path(__file__).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from whoop_mcp_server import server, load_config, load_tokens
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.fastmcp.server import StreamableHTTPASGIApp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whoop-mcp-http")

async def health(_: Any):
    return JSONResponse({"status": "ok", "time": datetime.utcnow().isoformat()})

def generate_oauth_url() -> str:
    """Generate Whoop OAuth authorization URL."""
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "config" / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    
    client_id = os.getenv("WHOOP_CLIENT_ID")
    redirect_uri = os.getenv("WHOOP_REDIRECT_URI")
    scopes = ["read:recovery", "read:cycles", "read:workout", "read:sleep", "read:profile", "read:body_measurement"]
    
    # Generate PKCE code verifier and challenge
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
    code_challenge_hash = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge_hash).decode().rstrip('=')
    state = secrets.token_urlsafe(32)
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    
    return f"https://api.prod.whoop.com/oauth/oauth2/auth?{urlencode(params)}"

async def handle_callback(request):
    """Handle OAuth callback from Whoop with authorization code"""
    try:
        # Get query parameters
        query_params = dict(request.query_params)
        code = query_params.get("code")
        state = query_params.get("state")
        scope = query_params.get("scope", "")
        
        if not code:
            return JSONResponse(
                {"error": "missing_code", "error_description": "Authorization code not provided"},
                status_code=400
            )
        
        logger.info(f"OAuth callback received - code: {code[:10]}..., state: {state}, scope: {scope}")
        
        # Return instructions to user
        return JSONResponse({
            "status": "success",
            "message": "Authorization code received successfully",
            "code_received": code[:10] + "...",
            "state": state,
            "scope": scope,
            "instructions": "Please use the token exchange script to complete authentication"
        })
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        return JSONResponse({"error": "Failed to handle callback", "message": str(e)}, status_code=500)

async def reauth(_: Any):
    """Generate and return OAuth authorization URL."""
    try:
        auth_url = generate_oauth_url()
        return HTMLResponse(f"""
        <html>
            <head>
                <title>Whoop Re-authentication</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
                    .btn {{ background-color: #4CAF50; color: white; padding: 15px 32px; text-align: center; 
                           text-decoration: none; display: inline-block; font-size: 16px; margin: 20px 0; 
                           cursor: pointer; border: none; border-radius: 4px; }}
                    .btn:hover {{ background-color: #45a049; }}
                    .info {{ background-color: #f0f8ff; border-left: 4px solid #2196F3; padding: 10px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <h1>🔐 Whoop Re-authentication Required</h1>
                <div class="info">
                    <p>Your Whoop access token has expired. Click the button below to re-authenticate.</p>
                </div>
                <a href="{auth_url}" class="btn">Authenticate with Whoop</a>
                <p><small>After authorizing, you'll be redirected back with a new token.</small></p>
            </body>
        </html>
        """)
    except Exception as e:
        logger.error(f"Error generating OAuth URL: {e}")
        return JSONResponse({"error": "Failed to generate OAuth URL", "message": str(e)}, status_code=500)

def main():
    load_config()
    load_tokens()
    
    # Create session manager
    session_manager = StreamableHTTPSessionManager(
        app=server,
        stateless=False,
        json_response=True
    )
    
    # Create the ASGI app wrapper (like FastMCP does)
    mcp_app = StreamableHTTPASGIApp(session_manager)
    
    # Create Starlette app with lifespan
    app = Starlette(
        routes=[
            Route("/mcp", endpoint=mcp_app, methods=["GET", "POST", "DELETE"]),
            Route("/health", endpoint=health, methods=["GET"]),
            Route("/reauth", endpoint=reauth, methods=["GET"]),
            Route("/callback", endpoint=handle_callback, methods=["GET"]),
        ],
        lifespan=lambda app: session_manager.run()
    )
    
    port = int(os.getenv("MCP_HTTP_PORT", "8003"))
    logger.info(f"Starting Whoop MCP Streamable HTTP server on port {port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
