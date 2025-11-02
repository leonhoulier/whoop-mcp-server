#!/usr/bin/env python3
"""
Proper MCP Server for Whoop API integration with OAuth support.
This server implements the MCP protocol with OAuth2 authentication.
"""

import asyncio
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    Resource,
    TextContent,
    Tool,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Whoop API configuration
WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v2"

# OAuth configuration
CLIENT_ID = None
CLIENT_SECRET = None
REDIRECT_URI = None

# Token storage
TOKEN_FILE = Path(__file__).parent.parent / "config" / "tokens.json"
access_token = None
refresh_token = None

# Create MCP server instance
server = Server("whoop-mcp-server")

def load_config() -> None:
    """Load configuration from environment variables."""
    global CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
    
    env_path = Path(__file__).parent.parent / "config" / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info("✅ Environment variables loaded")
    
    CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
    CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
    REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")
    
    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        logger.error("❌ Missing OAuth credentials in environment variables")

def load_tokens() -> None:
    """Load access and refresh tokens from file."""
    global access_token, refresh_token
    
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, "r") as f:
                tokens = json.load(f)
                access_token = tokens.get("access_token")
                refresh_token = tokens.get("refresh_token")
                logger.info("✅ Tokens loaded from file")
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")

def save_tokens(access: str, refresh: str) -> None:
    """Save access and refresh tokens to file."""
    global access_token, refresh_token
    
    access_token = access
    refresh_token = refresh
    
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "access_token": access,
            "refresh_token": refresh,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, f)
    
    # Secure the token file
    os.chmod(TOKEN_FILE, 0o600)
    logger.info("✅ Tokens saved securely")

async def refresh_access_token() -> bool:
    """Refresh the access token using the refresh token."""
    global access_token
    
    if not refresh_token:
        logger.warning("No refresh token available")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(WHOOP_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            })
            
            if response.status_code == 200:
                data = response.json()
                save_tokens(data["access_token"], data.get("refresh_token", refresh_token))
                logger.info("✅ Access token refreshed successfully")
                return True
            else:
                logger.error(f"❌ Token refresh failed: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return False

async def make_whoop_request(endpoint: str, params: Dict = None) -> Any:
    """Make an authenticated request to the Whoop API."""
    if not access_token:
        raise Exception("Not authenticated. Please authenticate first.")
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}{endpoint}"
    logger.info(f"Making request to: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 401:
                logger.warning("Token expired, attempting refresh...")
                if await refresh_access_token():
                    headers["Authorization"] = f"Bearer {access_token}"
                    response = await client.get(url, headers=headers, params=params)
                else:
                    raise Exception("Authentication expired. Please re-authenticate at https://mcp.leonhoulier.com/whoop/reauth")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API request failed: {response.status_code} {response.text}")
                raise Exception(f"API request failed: {response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        raise Exception(f"Request error: {str(e)}")

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="whoop://user/profile",
            name="User Profile",
            description="Leon Houlier's Whoop user profile information",
            mimeType="application/json"
        ),
        Resource(
            uri="whoop://auth/status",
            name="Authentication Status",
            description="Current authentication status and user info",
            mimeType="application/json"
        )
    ]

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_recovery_data",
            description="Get recovery data including recovery score, HRV, resting heart rate, SpO2, and skin temperature",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "Start date in ISO 8601 format (e.g., 2025-10-01T00:00:00Z)",
                        "format": "date-time"
                    },
                    "end": {
                        "type": "string", 
                        "description": "End date in ISO 8601 format (e.g., 2025-10-08T23:59:59Z)",
                        "format": "date-time"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (1-25)",
                        "minimum": 1,
                        "maximum": 25,
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_cycles_data",
            description="Get physiological cycle data including strain, calories, and heart rate metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "Start date in ISO 8601 format",
                        "format": "date-time"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in ISO 8601 format", 
                        "format": "date-time"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (1-25)",
                        "minimum": 1,
                        "maximum": 25,
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_latest_cycle",
            description="Get the most recent cycle data",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_average_strain",
            description="Calculate average strain over a specified number of days",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze (1-30)",
                        "minimum": 1,
                        "maximum": 30,
                        "default": 7
                    }
                }
            }
        ),
        Tool(
            name="check_auth_status",
            description="Check authentication status and get user profile",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_sleep_data",
            description="Get sleep data including sleep stages, performance %, quality score, respiratory rate, and efficiency",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "Start date in ISO 8601 format (e.g., 2025-10-01T00:00:00Z)",
                        "format": "date-time"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in ISO 8601 format (e.g., 2025-10-08T23:59:59Z)",
                        "format": "date-time"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (1-25)",
                        "minimum": 1,
                        "maximum": 25,
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_sleep_for_cycle",
            description="Get sleep data for a specific cycle by cycle ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "cycle_id": {
                        "type": "integer",
                        "description": "Cycle ID to retrieve sleep data for",
                        "format": "int64"
                    }
                }
            }
        ),
        Tool(
            name="get_latest_sleep",
            description="Get the most recent sleep data",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_workout_data",
            description="Get workout data including sport, strain score, heart rate zones, calories, and GPS data",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "Start date in ISO 8601 format (e.g., 2025-10-01T00:00:00Z)",
                        "format": "date-time"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in ISO 8601 format (e.g., 2025-10-08T23:59:59Z)",
                        "format": "date-time"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return (1-25)",
                        "minimum": 1,
                        "maximum": 25,
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_workout_by_id",
            description="Get specific workout by workout ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "workout_id": {
                        "type": "string",
                        "description": "Workout ID (UUID) to retrieve",
                        "format": "uuid"
                    }
                }
            }
        ),
        Tool(
            name="get_recent_workouts",
            description="Get recent workouts from the last 7 days",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_body_measurements",
            description="Get user body measurements including height, weight, and max heart rate",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_recovery_data":
            start = arguments.get("start")
            end = arguments.get("end") 
            limit = arguments.get("limit", 10)
            
            if not end:
                end = datetime.now(timezone.utc).isoformat()
            if not start:
                start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            data = await make_whoop_request("/recovery", {
                "start": start,
                "end": end,
                "limit": min(limit, 25)
            })
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
            
        elif name == "get_cycles_data":
            start = arguments.get("start")
            end = arguments.get("end")
            limit = arguments.get("limit", 10)
            
            if not end:
                end = datetime.now(timezone.utc).isoformat()
            if not start:
                start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            data = await make_whoop_request("/cycle", {
                "start": start,
                "end": end,
                "limit": min(limit, 25)
            })
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
            
        elif name == "get_latest_cycle":
            end = datetime.now(timezone.utc).isoformat()
            start = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            
            data = await make_whoop_request("/cycle", {
                "start": start,
                "end": end,
                "limit": 1
            })
            
            if data and data.get("records"):
                return [TextContent(
                    type="text",
                    text=json.dumps(data["records"][0], indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text="No cycle data available"
                )]
                
        elif name == "get_average_strain":
            days = arguments.get("days", 7)
            end = datetime.now(timezone.utc).isoformat()
            start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            data = await make_whoop_request("/cycle", {
                "start": start,
                "end": end,
                "limit": 25
            })
            
            if not data or not data.get("records"):
                return [TextContent(
                    type="text",
                    text="No cycle data available"
                )]
            
            strains = []
            for cycle in data["records"]:
                if cycle.get("score") and cycle["score"].get("strain"):
                    strains.append(cycle["score"]["strain"])
            
            if not strains:
                return [TextContent(
                    type="text",
                    text="No strain data available"
                )]
            
            result = {
                "average_strain": round(sum(strains) / len(strains), 2),
                "days_analyzed": days,
                "samples": len(strains),
                "date_range": {
                    "start": start,
                    "end": end
                }
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        elif name == "check_auth_status":
            if not access_token:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "authenticated": False,
                        "message": "Not authenticated with Whoop",
                        "instructions": "Please authenticate first"
                    }, indent=2)
                )]
            
            try:
                profile = await make_whoop_request("/user/profile/basic")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "authenticated": True,
                        "message": "Successfully authenticated with Whoop",
                        "user": profile
                    }, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "authenticated": False,
                        "message": f"Authentication error: {str(e)}",
                        "instructions": "Please re-authenticate"
                    }, indent=2)
                )]
        
        elif name == "get_sleep_data":
            start = arguments.get("start")
            end = arguments.get("end")
            limit = arguments.get("limit", 10)
            
            if not end:
                end = datetime.now(timezone.utc).isoformat()
            if not start:
                start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            data = await make_whoop_request("/activity/sleep", {
                "start": start,
                "end": end,
                "limit": min(limit, 25)
            })
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
            
        elif name == "get_sleep_for_cycle":
            cycle_id = arguments.get("cycle_id")
            
            if not cycle_id:
                return [TextContent(
                    type="text",
                    text="Error: cycle_id is required"
                )]
            
            data = await make_whoop_request(f"/cycle/{cycle_id}/sleep")
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
            
        elif name == "get_latest_sleep":
            end = datetime.now(timezone.utc).isoformat()
            
            data = await make_whoop_request("/activity/sleep", {
                "end": end,
                "limit": 1
            })
            
            if data and data.get("records"):
                return [TextContent(
                    type="text",
                    text=json.dumps(data["records"][0], indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text="No sleep data available"
                )]
        
        elif name == "get_workout_data":
            start = arguments.get("start")
            end = arguments.get("end")
            limit = arguments.get("limit", 10)
            
            if not end:
                end = datetime.now(timezone.utc).isoformat()
            if not start:
                start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            data = await make_whoop_request("/activity/workout", {
                "start": start,
                "end": end,
                "limit": min(limit, 25)
            })
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
            
        elif name == "get_workout_by_id":
            workout_id = arguments.get("workout_id")
            
            if not workout_id:
                return [TextContent(
                    type="text",
                    text="Error: workout_id is required"
                )]
            
            data = await make_whoop_request(f"/activity/workout/{workout_id}")
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
            
        elif name == "get_recent_workouts":
            end = datetime.now(timezone.utc).isoformat()
            start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            data = await make_whoop_request("/activity/workout", {
                "start": start,
                "end": end,
                "limit": 25
            })
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        
        elif name == "get_body_measurements":
            data = await make_whoop_request("/user/measurement/body")
            
            return [TextContent(
                type="text",
                text=json.dumps(data, indent=2)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
            
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    """Main entry point for the MCP server."""
    logger.info("🚀 Starting Whoop MCP Server with OAuth support...")
    
    # Load configuration and tokens
    load_config()
    load_tokens()
    
    if access_token:
        logger.info("✅ Found existing access token")
    else:
        logger.info("⚠️  No access token found. Authentication required.")
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="whoop-mcp-server",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
