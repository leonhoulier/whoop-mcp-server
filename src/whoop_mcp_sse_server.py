#!/usr/bin/env python3
import logging, os, sys
from datetime import datetime
from pathlib import Path
from typing import Any
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware

CURRENT_DIR = Path(__file__).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from whoop_mcp_server import server, load_config, load_tokens
from mcp.server.sse import SseServerTransport
from mcp.server.models import InitializationOptions
from mcp.server.auth.routes import create_auth_routes
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend, RequireAuthMiddleware
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.server.auth.provider import ProviderTokenVerifier
from whoop_oauth_provider import provider
from pydantic import AnyHttpUrl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whoop-mcp-sse")

sse = SseServerTransport("/messages/")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="whoop-mcp-sse",
                server_version="2.0.0",
                capabilities=server.get_capabilities(notification_options=None, experimental_capabilities={}),
            ),
        )
    return Response()

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
        
        # TODO: Exchange authorization code for access token using Whoop API
        # For now, return success message
        return JSONResponse({
            "status": "success",
            "message": "Authorization code received successfully",
            "code_received": code[:10] + "...",
            "state": state,
            "scope": scope
        })
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        return JSONResponse(
            {"error": "callback_error", "error_description": str(e)},
            status_code=500
        )

async def health(_: Any):
    return JSONResponse({"status": "ok", "time": datetime.utcnow().isoformat()})

def main():
    load_config()
    load_tokens()
    
    # OAuth configuration - Updated to use root domain for ChatGPT compatibility
    issuer_url = AnyHttpUrl("https://mcp.leonhoulier.com")
    service_documentation_url = AnyHttpUrl("https://mcp.leonhoulier.com/whoop/")
    
    # Enable client registration with valid scopes
    client_registration_options = ClientRegistrationOptions(
        enabled=True,
        valid_scopes=["read:recovery", "read:workout", "read:profile", "read:cycles"]
    )
    
    # Create OAuth routes
    oauth_routes = create_auth_routes(
        provider=provider,
        issuer_url=issuer_url,
        service_documentation_url=service_documentation_url,
        client_registration_options=client_registration_options
    )
    
    # Create token verifier and auth backend
    token_verifier = ProviderTokenVerifier(provider)
    auth_backend = BearerAuthBackend(token_verifier)
    
    # Create protected SSE handler with auth middleware
    protected_sse = AuthenticationMiddleware(
        RequireAuthMiddleware(handle_sse, required_scopes=["read:recovery"]),
        backend=auth_backend
    )
    
    # Create protected messages handler with auth middleware
    protected_messages = AuthenticationMiddleware(
        RequireAuthMiddleware(sse.handle_post_message, required_scopes=["read:recovery"]),
        backend=auth_backend
    )
    
    app = Starlette(
        routes=[
            # OAuth routes
            *oauth_routes,
            
            # Protected MCP routes
            Route("/sse", endpoint=protected_sse, methods=["GET"]),
            Mount("/messages/", app=protected_messages),
            
            # Public health check
            Route("/callback", endpoint=handle_callback, methods=["GET"]),
            Route("/health", endpoint=health, methods=["GET"]),
        ]
    )
    
    port = int(os.getenv("MCP_SSE_PORT", "8003"))
    logger.info(f"Starting Whoop MCP SSE server with OAuth on port {port}")
    logger.info(f"OAuth issuer URL: {issuer_url}")
    logger.info(f"OAuth metadata: {issuer_url}/.well-known/oauth-authorization-server")
    
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
