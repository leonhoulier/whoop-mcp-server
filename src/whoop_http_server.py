#!/usr/bin/env python3
"""
HTTP server for Whoop API integration.
This server exposes HTTP endpoints to query the Whoop API for cycles, recovery, and strain data.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
from fastapi import FastAPI, HTTPException
import uvicorn
from whoop import WhoopClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Whoop API Server", description="HTTP server for Whoop API integration")

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

@app.get("/auth/status")
def check_auth_status() -> Dict[str, Any]:
    """Check if we're authenticated with Whoop."""
    if not whoop_client:
        return {
            "authenticated": False,
            "message": "Not authenticated with Whoop"
        }
    
    try:
        # Test authentication by getting profile
        profile = whoop_client.get_profile()
        return {
            "authenticated": True,
            "message": "Successfully authenticated with Whoop",
            "profile": profile
        }
    except Exception as e:
        return {
            "authenticated": False,
            "message": f"Authentication error: {str(e)}"
        }

@app.get("/cycles/latest")
def get_latest_cycle() -> Dict[str, Any]:
    """Get the latest cycle data from Whoop."""
    if not whoop_client:
        raise HTTPException(status_code=401, detail="Not authenticated with Whoop")
    
    try:
        # Get today's date and yesterday's date
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Get cycle collection for the last day
        cycles = whoop_client.get_cycle_collection(start_date, end_date)
        logger.debug(f"Received cycles response: {cycles}")
        if not cycles:
            raise HTTPException(status_code=404, detail="No cycle data available")
        return cycles[0]  # Return the most recent cycle
    except Exception as e:
        logger.error(f"Error getting latest cycle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/strain/average")
def get_average_strain(days: int = 7) -> Dict[str, Any]:
    """Calculate average strain over the specified number of days."""
    if not whoop_client:
        raise HTTPException(status_code=401, detail="Not authenticated with Whoop")
    
    try:
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Get cycle collection
        cycles = whoop_client.get_cycle_collection(start_date, end_date)
        if not cycles:
            raise HTTPException(status_code=404, detail="No cycle data available")
            
        # Extract strain values
        strains = []
        for cycle in cycles:
            if cycle.get('score') and cycle['score'].get('strain'):
                strains.append(cycle['score']['strain'])
        
        if not strains:
            raise HTTPException(status_code=404, detail="No strain data available")
            
        return {
            "average_strain": sum(strains) / len(strains),
            "days_analyzed": days,
            "samples": len(strains)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cycles")
def get_cycles(limit: int = 10) -> List[Dict[str, Any]]:
    """Get multiple cycles from Whoop API."""
    if not whoop_client:
        raise HTTPException(status_code=401, detail="Not authenticated with Whoop")
    
    try:
        # Calculate date range based on limit
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=limit)).strftime("%Y-%m-%d")
        
        # Get cycle collection
        cycles = whoop_client.get_cycle_collection(start_date, end_date)
        if not cycles:
            raise HTTPException(status_code=404, detail="No cycle data available")
        return cycles[:limit]  # Return only the requested number of cycles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def main() -> None:
    """Main entry point for the server."""
    try:
        logger.info("Starting Whoop HTTP Server...")
        initialize_whoop_client()
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 