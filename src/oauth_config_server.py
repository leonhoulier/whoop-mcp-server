#!/usr/bin/env python3
"""
OAuth Configuration Server for MCP Agent Builders.
Provides OAuth configuration endpoints for agent builders to connect to the Whoop MCP server.
"""

import json
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / "config" / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

app = FastAPI(
    title="Whoop MCP OAuth Configuration",
    description="OAuth configuration for Whoop MCP Server",
    version="1.0.0"
)

@app.get("/", response_class=HTMLResponse)
def root():
    """Root endpoint with OAuth configuration information."""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Whoop MCP OAuth Configuration</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            h1 {{ color: #667eea; }}
            .config-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .oauth-config {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            pre {{ background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
            .button {{ display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
        </style>
    </head>
    <body>
        <h1>🤖 Whoop MCP OAuth Configuration</h1>
        
        <div class="config-box">
            <h2>📋 For Agent Builders (n8n, Zapier, etc.)</h2>
            <p>Use this configuration to connect to the Whoop MCP Server with OAuth2 authentication.</p>
            
            <div class="oauth-config">
                <h3>🔐 OAuth2 Configuration</h3>
                <p><strong>Client ID:</strong> <code>{os.getenv("WHOOP_CLIENT_ID", "Not configured")}</code></p>
                <p><strong>Client Secret:</strong> <code>{os.getenv("WHOOP_CLIENT_SECRET", "Not configured")[:20]}...</code></p>
                <p><strong>Authorization URL:</strong> <code>https://api.prod.whoop.com/oauth/oauth2/auth</code></p>
                <p><strong>Token URL:</strong> <code>https://api.prod.whoop.com/oauth/oauth2/token</code></p>
                <p><strong>Redirect URI:</strong> <code>https://mcp.leonhoulier.com/whoop/callback</code></p>
                <p><strong>Scopes:</strong> <code>read:recovery read:cycles read:workout read:sleep read:profile read:body_measurement</code></p>
            </div>
            
            <h3>🎯 MCP Server Details</h3>
            <p><strong>Server URL:</strong> <code>https://mcp.leonhoulier.com/whoop/</code></p>
            <p><strong>Protocol:</strong> MCP (Model Context Protocol)</p>
            <p><strong>Authentication:</strong> OAuth2 Authorization Code Flow</p>
            
            <h3>📡 Available Tools</h3>
            <ul>
                <li><code>get_recovery_data</code> - Recovery metrics (score, HRV, resting HR, SpO2)</li>
                <li><code>get_cycles_data</code> - Strain and cycle data</li>
                <li><code>get_latest_cycle</code> - Most recent cycle data</li>
                <li><code>get_average_strain</code> - Average strain calculation</li>
                <li><code>check_auth_status</code> - Authentication status</li>
            </ul>
        </div>
        
        <div class="config-box">
            <h2>🔗 Quick Links</h2>
            <a href="/oauth-config" class="button">Get OAuth Config (JSON)</a>
            <a href="/mcp-config" class="button">Get MCP Config (JSON)</a>
            <a href="https://mcp.leonhoulier.com/whoop/" class="button">Main Documentation</a>
        </div>
        
        <div class="config-box">
            <h2>📖 Setup Instructions</h2>
            <ol>
                <li><strong>In your agent builder:</strong> Add new MCP server connection</li>
                <li><strong>Server URL:</strong> <code>https://mcp.leonhoulier.com/whoop/</code></li>
                <li><strong>Authentication:</strong> Select "OAuth2"</li>
                <li><strong>OAuth Config:</strong> Use the values above or fetch from <code>/oauth-config</code></li>
                <li><strong>Test Connection:</strong> Use <code>check_auth_status</code> tool</li>
            </ol>
        </div>
    </body>
    </html>
    """)

@app.get("/oauth-config")
def get_oauth_config():
    """Get OAuth2 configuration in JSON format."""
    return JSONResponse(content={
        "clientId": os.getenv(WHOOP_CLIENT_ID),
        "clientSecret": os.getenv("WHOOP_CLIENT_SECRET"),
        "authorizationUrl": "https://api.prod.whoop.com/oauth/oauth2/auth",
        "tokenUrl": "https://api.prod.whoop.com/oauth/oauth2/token",
        "redirectUri": "https://mcp.leonhoulier.com/whoop/callback",
        "scope": "read:recovery read:cycles read:workout read:sleep read:profile read:body_measurement"
    })

@app.get("/mcp-config")
def get_mcp_config():
    """Get MCP server configuration in JSON format."""
    return JSONResponse(content={
        "mcpServers": {
            "whoop-mcp": {
                "command": "python",
                "args": ["/home/ubuntu/whoop-mcp-server/src/whoop_mcp_server.py"],
                "env": {
                    "WHOOP_CLIENT_ID": os.getenv(WHOOP_CLIENT_ID),
                    "WHOOP_CLIENT_SECRET": os.getenv("WHOOP_CLIENT_SECRET"),
                    "WHOOP_REDIRECT_URI": "https://mcp.leonhoulier.com/whoop/callback"
                }
            }
        },
        "oauth": {
            "whoop": {
                "clientId": os.getenv(WHOOP_CLIENT_ID),
                "clientSecret": os.getenv("WHOOP_CLIENT_SECRET"),
                "authorizationUrl": "https://api.prod.whoop.com/oauth/oauth2/auth",
                "tokenUrl": "https://api.prod.whoop.com/oauth/oauth2/token",
                "redirectUri": "https://mcp.leonhoulier.com/whoop/callback",
                "scope": "read:recovery read:cycles read:workout read:sleep read:profile read:body_measurement"
            }
        }
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
