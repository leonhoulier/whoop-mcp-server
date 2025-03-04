#!/usr/bin/env python3
"""
MCP server for Whoop API integration.
This server exposes methods to query the Whoop API for cycles, recovery, and strain data.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import logging

from mcp.server.fastmcp import FastMCP
from whoop import WhoopClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("Whoop API MCP Server")

# Initialize Whoop client
whoop_client: Optional[WhoopClient] = None

def initialize_whoop_client() -> None:
    """Initialize the Whoop client using environment variables."""
    global whoop_client
    
    # Load environment variables
    env_path = Path(__file__).parent.parent / 'config' / '.env'
    logger.info(f"Looking for .env file at: {env_path}")
    
    if not env_path.exists():
        logger.error(f"Environment file not found at {env_path}")
        return
    
    load_dotenv(dotenv_path=env_path)
    logger.info("Environment variables loaded")
    
    # Get credentials
    email = os.getenv("WHOOP_EMAIL")
    password = os.getenv("WHOOP_PASSWORD")
    
    if not email or not password:
        logger.error("Missing Whoop credentials in environment variables")
        return
        
    try:
        whoop_client = WhoopClient(username=email, password=password)
        logger.info("Successfully authenticated with Whoop API")
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")

@mcp.tool()
def get_latest_cycle() -> Dict[str, Any]:
    """
    Get the latest cycle data from Whoop.
    
    Returns:
        Dictionary containing the latest cycle data
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        cycles = whoop_client.cycles.get_cycles(limit=1)
        return cycles[0] if cycles else {"error": "No cycle data available"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_average_strain(days: int = 7) -> Dict[str, Any]:
    """
    Calculate average strain over the specified number of days.
    
    Args:
        days: Number of days to analyze (default: 7)
        
    Returns:
        Dictionary containing average strain data
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        cycles = whoop_client.cycles.get_cycles(limit=days)
        if not cycles:
            return {"error": "No cycle data available"}
            
        strains = [cycle.get('strain', 0) for cycle in cycles if cycle.get('strain') is not None]
        if not strains:
            return {"error": "No strain data available"}
            
        return {
            "average_strain": sum(strains) / len(strains),
            "days_analyzed": days,
            "samples": len(strains)
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def check_auth_status() -> Dict[str, Any]:
    """
    Check if we're authenticated with Whoop.
    
    Returns:
        Dictionary containing authentication status
    """
    return {
        "authenticated": whoop_client is not None,
        "message": "Successfully authenticated with Whoop" if whoop_client else "Not authenticated with Whoop"
    }

@mcp.tool()
def get_cycles(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get multiple cycles from Whoop API.
    
    Args:
        limit: Number of cycles to fetch (default: 10)
        
    Returns:
        List of cycle data dictionaries
    """
    if not whoop_client:
        return [{"error": "Not authenticated with Whoop"}]
    
    try:
        cycles = whoop_client.cycles.get_cycles(limit=limit)
        return cycles
    except Exception as e:
        return [{"error": str(e)}]

def main() -> None:
    """Main entry point for the server."""
    try:
        logger.info("Starting Whoop MCP Server...")
        initialize_whoop_client()
        logger.info("Running MCP server with stdio transport")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 