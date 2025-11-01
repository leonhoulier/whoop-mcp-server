#!/usr/bin/env python3
"""
Whoop MCP Server - Public Documentation Page

This server provides a public documentation page for the Whoop MCP server.
"""

import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Whoop MCP Server Documentation", version="1.13.2")

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
            <div class="endpoint">https://mcp.leonhoulier.com/whoop/mcp</div>
            
            <div class="info">
                <strong>📋 For ChatGPT Dev Mode / Claude Desktop / Cursor:</strong><br>
                Use the connection URL above. The server uses OAuth 2.1 with PKCE for authentication.
            </div>
        </div>

        <div class="section">
            <h2>🔐 Authentication</h2>
            <p>Whoop MCP uses OAuth 2.1 with PKCE for secure authentication. The flow works as follows:</p>
            <ol>
                <li>Add the Whoop MCP server to your Cursor or Claude Desktop configuration</li>
                <li>The server will automatically initiate an OAuth 2.1 flow with PKCE</li>
                <li>You'll be prompted to authorize access to your Whoop account</li>
                <li>After authorization, tokens are securely stored and the connection is established</li>
            </ol>
            
            <div class="warning">
                <strong>⚠️ Token Expiration:</strong> Whoop tokens expire after 24 hours and require re-authentication. 
                Visit <a href="https://mcp.leonhoulier.com/whoop/reauth">https://mcp.leonhoulier.com/whoop/reauth</a> when needed.
            </div>
            
            <div class="info">
                <strong>📖 Whoop API Documentation:</strong> <a href="https://api.prod.whoop.com/developer/doc/openapi.json" target="_blank">OpenAPI Spec</a>
            </div>
        </div>

        <div class="section">
            <h2>🛠️ Available MCP Tools (12 Tools)</h2>
            
            <h3>Recovery Data</h3>
            <div class="tool-list">
                <div class="tool-item">
                    <strong>get_recovery_data</strong><br>
                    <em>Get recovery data including recovery score, HRV, resting heart rate, SpO2, and skin temperature</em>
                </div>
            </div>

            <h3>Cycles & Strain</h3>
            <div class="tool-list">
                <div class="tool-item">
                    <strong>get_cycles_data</strong><br>
                    <em>Get physiological cycle data including strain, calories, and heart rate metrics</em>
                </div>
                <div class="tool-item">
                    <strong>get_latest_cycle</strong><br>
                    <em>Get the most recent cycle data</em>
                </div>
                <div class="tool-item">
                    <strong>get_average_strain</strong><br>
                    <em>Calculate average strain over a specified number of days (1-30)</em>
                </div>
            </div>

            <h3>Sleep Data</h3>
            <div class="tool-list">
                <div class="tool-item">
                    <strong>get_sleep_data</strong><br>
                    <em>Get sleep data including sleep stages, performance %, quality score, respiratory rate, and efficiency</em>
                </div>
                <div class="tool-item">
                    <strong>get_sleep_for_cycle</strong><br>
                    <em>Get sleep data for a specific cycle by cycle ID</em>
                </div>
                <div class="tool-item">
                    <strong>get_latest_sleep</strong><br>
                    <em>Get the most recent sleep data</em>
                </div>
            </div>

            <h3>Workout Data</h3>
            <div class="tool-list">
                <div class="tool-item">
                    <strong>get_workout_data</strong><br>
                    <em>Get workout data including sport, strain score, heart rate zones, calories, and GPS data</em>
                </div>
                <div class="tool-item">
                    <strong>get_workout_by_id</strong><br>
                    <em>Get specific workout by workout ID (UUID)</em>
                </div>
                <div class="tool-item">
                    <strong>get_recent_workouts</strong><br>
                    <em>Get recent workouts from the last 7 days</em>
                </div>
            </div>

            <h3>Body Measurements</h3>
            <div class="tool-list">
                <div class="tool-item">
                    <strong>get_body_measurements</strong><br>
                    <em>Get user body measurements including height, weight, and max heart rate</em>
                </div>
            </div>

            <h3>Authentication</h3>
            <div class="tool-list">
                <div class="tool-item">
                    <strong>check_auth_status</strong><br>
                    <em>Check authentication status and get user profile</em>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Key Features</h2>
            <ul>
                <li><strong>Recovery Tracking:</strong> Monitor recovery scores, HRV, and heart rate metrics</li>
                <li><strong>Sleep Analysis:</strong> Track sleep stages, quality, and respiratory rate</li>
                <li><strong>Workout Insights:</strong> Analyze workouts with strain scores, heart rate zones, and GPS data</li>
                <li><strong>Cycle Management:</strong> Track physiological cycles with strain and calorie data</li>
                <li><strong>Body Metrics:</strong> Monitor height, weight, and heart rate parameters</li>
                <li><strong>Streamable HTTP:</strong> Modern MCP protocol with OAuth 2.1 authentication</li>
            </ul>
        </div>

        <div class="section">
            <h2>📋 Example Queries</h2>
            <div class="code-block">
- "What's my recovery score for yesterday?"
- "Get my latest sleep data"
- "Show me my workouts from the last week"
- "What's my average strain over the past 7 days?"
- "Get my body measurements"
- "Show me recent cycles with strain data"
            </div>
        </div>

        <div class="section">
            <h2>📊 Server Status</h2>
            <p><strong>Status:</strong> <span class="status status-online">Online</span></p>
            <p><strong>Version:</strong> 1.13.2</p>
            <p><strong>Transport:</strong> Streamable HTTP</p>
            <p><strong>API:</strong> Whoop Developer API v2</p>
            <p><strong>Last Updated:</strong> {today}</p>
        </div>

        <div class="section">
            <h2>📚 Resources</h2>
            <ul>
                <li><strong>Whoop API:</strong> <a href="https://api.prod.whoop.com/developer/doc/openapi.json" target="_blank">OpenAPI Specification</a></li>
                <li><strong>MCP Protocol:</strong> <a href="https://modelcontextprotocol.io/" target="_blank">modelcontextprotocol.io</a></li>
                <li><strong>Server Endpoint:</strong> <a href="https://mcp.leonhoulier.com/whoop/mcp">https://mcp.leonhoulier.com/whoop/mcp</a></li>
                <li><strong>Re-authentication:</strong> <a href="https://mcp.leonhoulier.com/whoop/reauth">https://mcp.leonhoulier.com/whoop/reauth</a></li>
            </ul>
        </div>

        <div class="footer">
            <p>Whoop MCP Server - AI-powered interface for Whoop fitness data</p>
            <p>Built with MCP SDK and Whoop Developer API</p>
            <p style="margin-top: 1.5rem;"><a href="https://leonhoulier.com/">Léon Houlier</a> &copy; 2025</p>
        </div>
    </div>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WHOOP_DOCS_PORT", "8005"))
    uvicorn.run(app, host="0.0.0.0", port=port)

