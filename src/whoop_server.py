#!/usr/bin/env python3
"""
MCP server for Whoop API integration.
This server exposes methods to query the Whoop API for cycles, recovery, and strain data.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
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
        Dictionary containing the latest cycle data including recovery score
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        # Get today's date and yesterday's date
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Get cycle collection for the last day - pass as positional arguments
        cycles = whoop_client.get_cycle_collection(start_date, end_date)
        logger.debug(f"Received cycles response: {cycles}")
        
        if not cycles:
            return {"error": "No cycle data available"}
            
        latest_cycle = cycles[0]  # Most recent cycle
        
        # Extract recovery score if available
        recovery_score = None
        if latest_cycle.get('score') and latest_cycle['score'].get('recovery'):
            recovery_score = latest_cycle['score']['recovery']
            
        return {
            "cycle": latest_cycle,
            "recovery_score": recovery_score,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting latest cycle: {str(e)}")
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
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Get cycle collection
        cycles = whoop_client.get_cycle_collection(start_date, end_date)
        if not cycles:
            return {"error": "No cycle data available"}
            
        # Extract strain values
        strains = []
        for cycle in cycles:
            if cycle.get('score') and cycle['score'].get('strain'):
                strains.append(cycle['score']['strain'])
        
        if not strains:
            return {"error": "No strain data available"}
            
        return {
            "average_strain": sum(strains) / len(strains),
            "days_analyzed": days,
            "samples": len(strains),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error calculating average strain: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def check_auth_status() -> Dict[str, Any]:
    """
    Check if we're authenticated with Whoop.
    
    Returns:
        Dictionary containing authentication status and profile info if available
    """
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
            "profile": profile,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "authenticated": False,
            "message": f"Authentication error: {str(e)}"
        }

@mcp.tool()
def get_cycles(days: int = 10) -> List[Dict[str, Any]]:
    """
    Get multiple cycles from Whoop API.
    
    Args:
        days: Number of days to fetch (default: 10)
        
    Returns:
        List of cycle data dictionaries
    """
    if not whoop_client:
        return [{"error": "Not authenticated with Whoop"}]
    
    try:
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Get cycle collection
        cycles = whoop_client.get_cycle_collection(start_date, end_date)
        if not cycles:
            return [{"error": "No cycle data available"}]
            
        return [{
            "cycle": cycle,
            "timestamp": datetime.now().isoformat()
        } for cycle in cycles]
    except Exception as e:
        logger.error(f"Error getting cycles: {str(e)}")
        return [{"error": str(e)}]

# NEW: Specific ID-Based Retrieval Methods

@mcp.tool()
def get_cycle_by_id(cycle_id: str) -> Dict[str, Any]:
    """
    Get a specific cycle by its ID from Whoop API.
    
    Args:
        cycle_id: The ID of the cycle to retrieve
        
    Returns:
        Dictionary containing the cycle data
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        cycle = whoop_client.get_cycle(cycle_id)  # Assumes this method exists
        if not cycle:
            return {"error": f"No cycle found with ID {cycle_id}"}
        return {
            "cycle": cycle,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cycle {cycle_id}: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def get_recovery_by_id(recovery_id: str) -> Dict[str, Any]:
    """
    Get a specific recovery entry by its ID from Whoop API.
    
    Args:
        recovery_id: The ID of the recovery entry to retrieve
        
    Returns:
        Dictionary containing the recovery data
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        recovery = whoop_client.get_recovery(recovery_id)  # Assumes this method exists
        if not recovery:
            return {"error": f"No recovery found with ID {recovery_id}"}
        return {
            "recovery": recovery,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting recovery {recovery_id}: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def get_sleep_by_id(sleep_id: str) -> Dict[str, Any]:
    """
    Get a specific sleep entry by its ID from Whoop API.
    
    Args:
        sleep_id: The ID of the sleep entry to retrieve
        
    Returns:
        Dictionary containing the sleep data
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        sleep = whoop_client.get_sleep(sleep_id)  # Assumes this method exists
        if not sleep:
            return {"error": f"No sleep found with ID {sleep_id}"}
        return {
            "sleep": sleep,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting sleep {sleep_id}: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def get_workout_by_id(workout_id: str) -> Dict[str, Any]:
    """
    Get a specific workout by its ID from Whoop API.
    
    Args:
        workout_id: The ID of the workout to retrieve
        
    Returns:
        Dictionary containing the workout data
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        workout = whoop_client.get_workout(workout_id)  # Assumes this method exists
        if not workout:
            return {"error": f"No workout found with ID {workout_id}"}
        return {
            "workout": workout,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting workout {workout_id}: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def get_strain_by_id(strain_id: str) -> Dict[str, Any]:
    """
    Get a specific strain entry by its ID from Whoop API.
    
    Args:
        strain_id: The ID of the strain entry to retrieve
        
    Returns:
        Dictionary containing the strain data
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        strain = whoop_client.get_strain(strain_id)  # Assumes this method exists
        if not strain:
            return {"error": f"No strain found with ID {strain_id}"}
        return {
            "strain": strain,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting strain {strain_id}: {str(e)}")
        return {"error": str(e)}

# NEW: Standalone Data Retrieval Methods

@mcp.tool()
def get_recoveries(days: int = 10) -> List[Dict[str, Any]]:
    """
    Get multiple recovery entries from Whoop API, independent of cycles.
    
    Args:
        days: Number of days to fetch (default: 10)
        
    Returns:
        List of recovery data dictionaries
    """
    if not whoop_client:
        return [{"error": "Not authenticated with Whoop"}]
    
    try:
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Get recovery collection
        recoveries = whoop_client.get_recovery_collection(start_date, end_date)  # Assumes this method exists
        if not recoveries:
            return [{"error": "No recovery data available"}]
            
        return [{
            "recovery": recovery,
            "timestamp": datetime.now().isoformat()
        } for recovery in recoveries]
    except Exception as e:
        logger.error(f"Error getting recoveries: {str(e)}")
        return [{"error": str(e)}]

@mcp.tool()
def get_sleeps(days: int = 10) -> List[Dict[str, Any]]:
    """
    Get multiple sleep entries from Whoop API, independent of cycles.
    
    Args:
        days: Number of days to fetch (default: 10)
        
    Returns:
        List of sleep data dictionaries
    """
    if not whoop_client:
        return [{"error": "Not authenticated with Whoop"}]
    
    try:
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Get sleep collection
        sleeps = whoop_client.get_sleep_collection(start_date, end_date)  # Assumes this method exists
        if not sleeps:
            return [{"error": "No sleep data available"}]
            
        return [{
            "sleep": sleep,
            "timestamp": datetime.now().isoformat()
        } for sleep in sleeps]
    except Exception as e:
        logger.error(f"Error getting sleeps: {str(e)}")
        return [{"error": str(e)}]

@mcp.tool()
def get_workouts(days: int = 10) -> List[Dict[str, Any]]:
    """
    Get multiple workout entries from Whoop API.
    
    Args:
        days: Number of days to fetch (default: 10)
        
    Returns:
        List of workout data dictionaries
    """
    if not whoop_client:
        return [{"error": "Not authenticated with Whoop"}]
    
    try:
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Get workout collection
        workouts = whoop_client.get_workout_collection(start_date, end_date)  # Assumes this method exists
        if not workouts:
            return [{"error": "No workout data available"}]
            
        return [{
            "workout": workout,
            "timestamp": datetime.now().isoformat()
        } for workout in workouts]
    except Exception as e:
        logger.error(f"Error getting workouts: {str(e)}")
        return [{"error": str(e)}]

@mcp.tool()
def get_strains(days: int = 10) -> List[Dict[str, Any]]:
    """
    Get multiple strain entries from Whoop API, independent of cycles.
    
    Args:
        days: Number of days to fetch (default: 10)
        
    Returns:
        List of strain data dictionaries
    """
    if not whoop_client:
        return [{"error": "Not authenticated with Whoop"}]
    
    try:
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Get strain collection
        strains = whoop_client.get_strain_collection(start_date, end_date)  # Assumes this method exists
        if not strains:
            return [{"error": "No strain data available"}]
            
        return [{
            "strain": strain,
            "timestamp": datetime.now().isoformat()
        } for strain in strains]
    except Exception as e:
        logger.error(f"Error getting strains: {str(e)}")
        return [{"error": str(e)}]

# User Measurements Retrieval

@mcp.tool()
def get_user_body_measurements() -> Dict[str, Any]:
    """
    Get the user's body measurements from Whoop.
    Uses /v1/user/measurement/body endpoint.
    
    Returns:
        Dictionary containing height, weight, and max heart rate
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        # API endpoint: GET /v1/user/measurement/body
        measurements = whoop_client.get_body_measurement()
        
        if not measurements:
            return {"error": "No body measurement data available"}
            
        return {
            "measurements": measurements,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting body measurements: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def get_latest_recovery() -> Dict[str, Any]:
    """
    Get the latest recovery data from Whoop.
    Uses /v1/recovery endpoint.
    
    Returns:
        Dictionary containing latest recovery data
    """
    if not whoop_client:
        return {"error": "Not authenticated with Whoop"}
    
    try:
        # Get today's recovery data
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # API endpoint: GET /v1/recovery
        # Parameters: start, end, limit=10 (default)
        recoveries = whoop_client.get_recovery_collection(start_date, end_date)
        
        if not recoveries or not recoveries.get('records'):
            return {"error": "No recent recovery data available"}
            
        # Get the first record (most recent as API sorts by sleep start time descending)
        latest_recovery = recoveries['records'][0]
        
        return {
            "recovery": latest_recovery,
            "recovery_score": latest_recovery.get('score', {}).get('recovery_score'),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting latest recovery: {str(e)}")
        return {"error": str(e)}

# Team-Related Functionality (Optional)

@mcp.tool()
def get_team_members(team_id: str) -> List[Dict[str, Any]]:
    """
    Get team member data from Whoop API.
    
    Args:
        team_id: The ID of the team to retrieve members for
        
    Returns:
        List of team member data dictionaries
    """
    if not whoop_client:
        return [{"error": "Not authenticated with Whoop"}]
    
    try:
        members = whoop_client.get_team_members(team_id)  # Assumes this method exists
        if not members:
            return [{"error": f"No members found for team {team_id}"}]
        return [{
            "member": member,
            "timestamp": datetime.now().isoformat()
        } for member in members]
    except Exception as e:
        logger.error(f"Error getting team members for team {team_id}: {str(e)}")
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