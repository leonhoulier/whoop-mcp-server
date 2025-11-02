#!/usr/bin/env python3
"""
Whoop MCP Server - Public Documentation Page

This server provides a public documentation page for the Whoop MCP server.
It includes MCP-only documentation and OAuth connection instructions.
"""

import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI(title="Whoop MCP Server Documentation", version="2.0.0")

@app.get("/", response_class=HTMLResponse)
async def documentation():
    today = datetime.now().strftime("%Y-%m-%d")
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Whoop MCP Server - Léon Houlier</title>
    <link rel="stylesheet" href="https://mcp.leonhoulier.com/style.css">
</head>
<body>
    <nav class="breadcrumb">
        <a href="https://leonhoulier.com/">Léon Houlier</a>
        <span>/</span>
        <a href="https://mcp.leonhoulier.com/">MCP Servers</a>
        <span>/</span>
        <span>Whoop</span>
    </nav>

    <div class="container">
        <h1>🏃‍♂️ Whoop MCP Server <span class="status status-online">Online</span></h1>
        
        <div class="section">
            <h2>🔗 MCP Connection</h2>
            <p><strong>Connection URL:</strong></p>
            <div class="endpoint">https://mcp.leonhoulier.com/whoop/sse</div>
            
            <div class="info">
                <strong>📋 For ChatGPT Dev Mode / Claude Desktop:</strong><br>
                Use the connection URL above. The server supports OAuth 2.1 with PKCE for secure authentication.
            </div>
        </div>

        <div class="section">
            <h2>🔐 OAuth 2.1 Authentication</h2>
            
            <div class="oauth-flow">
                <h3>OAuth Discovery</h3>
                <div class="endpoint">https://mcp.leonhoulier.com/whoop/.well-known/oauth-authorization-server</div>
                
                <h3>Supported OAuth Flow:</h3>
                <div class="step">
                    <strong>1. Dynamic Client Registration</strong><br>
                    POST to <code>/whoop/register</code> to register your client
                </div>
                <div class="step">
                    <strong>2. Authorization Code Flow with PKCE</strong><br>
                    Redirect to <code>/whoop/authorize</code> with PKCE parameters
                </div>
                <div class="step">
                    <strong>3. Token Exchange</strong><br>
                    POST to <code>/whoop/token</code> to exchange authorization code for access token
                </div>
                <div class="step">
                    <strong>4. Authenticated MCP Connection</strong><br>
                    Connect to SSE endpoint with Bearer token in Authorization header
                </div>
            </div>

            <div class="warning">
                <strong>⚠️ Important:</strong> Each MCP client session gets unique OAuth tokens for enhanced security.
            </div>
        </div>

        <div class="section">
            <h2>🛠️ Available MCP Tools</h2>
            <div class="tool-list">
                <div class="tool-item">
                    <strong>get_recovery_data</strong><br>
                    <em>Retrieve recovery metrics for specified date range</em><br>
                    <code>Parameters:</code> start (date), end (date)
                </div>
                <div class="tool-item">
                    <strong>get_cycles_data</strong><br>
                    <em>Get strain and cycle data for date range</em><br>
                    <code>Parameters:</code> start (date), end (date)
                </div>
                <div class="tool-item">
                    <strong>get_latest_cycle</strong><br>
                    <em>Get the most recent cycle data</em><br>
                    <code>Parameters:</code> None
                </div>
                <div class="tool-item">
                    <strong>get_average_strain</strong><br>
                    <em>Calculate average strain for date range</em><br>
                    <code>Parameters:</code> start (date), end (date)
                </div>
                <div class="tool-item">
                    <strong>check_auth_status</strong><br>
                    <em>Check current authentication status</em><br>
                    <code>Parameters:</code> None
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📋 Recommended System Prompt for AI Agents</h2>
            <div class="code-block">
You are a Whoop fitness data assistant. You have access to a Whoop MCP server that provides recovery, strain, and cycle data.

<strong>Connection Details:</strong>
- MCP Server: https://mcp.leonhoulier.com/whoop/sse
- Authentication: OAuth 2.1 with PKCE
- OAuth Discovery: https://mcp.leonhoulier.com/whoop/.well-known/oauth-authorization-server

<strong>Available Tools:</strong>
- get_recovery_data: Get recovery scores for date ranges
- get_cycles_data: Get strain and cycle data
- get_latest_cycle: Get most recent cycle
- get_average_strain: Calculate average strain
- check_auth_status: Verify authentication

<strong>Usage Guidelines:</strong>
1. Always authenticate using OAuth 2.1 flow before making tool calls
2. Use proper date formatting (YYYY-MM-DD) for date parameters
3. Provide helpful insights about recovery trends, strain patterns, and cycle analysis
4. Suggest actionable recommendations based on the data

<strong>Example Queries:</strong>
- "What was my recovery score yesterday?"
- "Show me my strain data for the last week"
- "Compare my recovery from this week to last week"
- "What's my average strain for this month?"
            </div>
        </div>

        <div class="section">
            <h2>🔧 OAuth Endpoints</h2>
            <div class="tool-list">
                <div class="tool-item">
                    <strong>OAuth Discovery</strong><br>
                    <code>GET /whoop/.well-known/oauth-authorization-server</code><br>
                    Returns OAuth server metadata
                </div>
                <div class="tool-item">
                    <strong>Client Registration</strong><br>
                    <code>POST /whoop/register</code><br>
                    Register a new OAuth client
                </div>
                <div class="tool-item">
                    <strong>Authorization</strong><br>
                    <code>GET /whoop/authorize</code><br>
                    Start OAuth authorization flow
                </div>
                <div class="tool-item">
                    <strong>Token Exchange</strong><br>
                    <code>POST /whoop/token</code><br>
                    Exchange authorization code for access token
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Server Status</h2>
            <p><strong>Status:</strong> <span class="status status-online">Online</span></p>
            <p><strong>Version:</strong> 2.0.0</p>
            <p><strong>Transport:</strong> Server-Sent Events (SSE)</p>
            <p><strong>Authentication:</strong> OAuth 2.1 with PKCE</p>
            <p><strong>Last Updated:</strong> {today}</p>
        </div>

        <div class="footer">
            <p>Whoop MCP Server - Providing secure access to Whoop fitness data via MCP protocol</p>
            <p>Built with FastAPI, MCP Python SDK, and OAuth 2.1</p>
            <p style="margin-top: 1.5rem;"><a href="https://leonhoulier.com/">Léon Houlier</a> &copy; 2025</p>
        </div>
    </div>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WHOOP_HTTP_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
