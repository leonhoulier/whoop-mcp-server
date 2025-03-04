import os
import sys
import json
import logging
import socket
import threading
import traceback
from typing import Optional, Dict, Any, List

# Add debug output to stderr for Claude Desktop
print("Starting Whoop MCP Server...", file=sys.stderr)
print(f"Python version: {sys.version}", file=sys.stderr)
print(f"Current directory: {os.getcwd()}", file=sys.stderr)
print(f"Script path: {os.path.abspath(__file__)}", file=sys.stderr)
print(f"Arguments: {sys.argv}", file=sys.stderr)
print(f"Environment variables: {os.environ.get('PATH')}", file=sys.stderr)

try:
    from whoop import WhoopClient
    print("Successfully imported WhoopClient", file=sys.stderr)
except ImportError as e:
    print(f"Error importing WhoopClient: {e}", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("Successfully imported load_dotenv", file=sys.stderr)
except ImportError as e:
    print(f"Error importing load_dotenv: {e}", file=sys.stderr)
    sys.exit(1)

from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent / 'config' / '.env'
print(f"Looking for .env file at: {env_path}", file=sys.stderr)
if not env_path.exists():
    print(f"ERROR: Environment file not found at {env_path}", file=sys.stderr)
    logger.error(f"Environment file not found at {env_path}")
    sys.exit(1)

load_dotenv(dotenv_path=env_path)
print("Environment variables loaded", file=sys.stderr)

# MCP Server capabilities
SERVER_CAPABILITIES = {
    "server": {
        "name": "Whoop MCP Server",
        "version": "0.1.0",
        "description": "MCP server for accessing Whoop fitness data"
    },
    "resources": [
        {
            "name": "whoop",
            "description": "Access to Whoop fitness data"
        }
    ],
    "tools": [
        {
            "name": "getLatestCycle",
            "description": "Get the latest Whoop cycle data"
        },
        {
            "name": "getAverageStrain",
            "description": "Calculate average strain over the last N days"
        },
        {
            "name": "checkAuthStatus",
            "description": "Check if we're authenticated with Whoop"
        }
    ]
}

class WhoopAPI:
    def __init__(self):
        self.client: Optional[WhoopClient] = None
        # Try to authenticate on startup if credentials are available
        email = os.getenv("WHOOP_EMAIL")
        password = os.getenv("WHOOP_PASSWORD")
        if email and password:
            self.authenticate_with_env()
        
    def authenticate_with_env(self) -> bool:
        """Authenticate with Whoop API using environment variables."""
        email = os.getenv("WHOOP_EMAIL")
        password = os.getenv("WHOOP_PASSWORD")
        
        if not email or not password:
            logger.error("Missing Whoop credentials in environment variables")
            return False
            
        return self.authenticate(email, password)
        
    def authenticate(self, email: str, password: str) -> bool:
        """Authenticate with Whoop API using email and password."""
        try:
            self.client = WhoopClient(username=email, password=password)
            logger.info("Successfully authenticated with Whoop API")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def get_latest_cycle(self) -> Dict[str, Any]:
        """Fetch the latest cycle data from Whoop API."""
        if not self.client:
            logger.warning("Attempted to fetch cycle data without authentication")
            return {"error": "Not authenticated with Whoop"}
        
        try:
            cycles = self.client.cycles.get_cycles(limit=1)
            logger.info("Successfully fetched latest cycle data")
            return cycles[0] if cycles else {"error": "No cycle data available"}
        except Exception as e:
            logger.error(f"Failed to fetch cycle data: {str(e)}")
            return {"error": str(e)}

    def get_cycles(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch multiple cycles from Whoop API."""
        if not self.client:
            logger.warning("Attempted to fetch cycles without authentication")
            return [{"error": "Not authenticated with Whoop"}]
        
        try:
            cycles = self.client.cycles.get_cycles(limit=limit)
            logger.info(f"Successfully fetched {limit} cycles")
            return cycles
        except Exception as e:
            logger.error(f"Failed to fetch cycles: {str(e)}")
            return [{"error": str(e)}]
            
    def get_average_strain(self, days: int) -> Dict[str, Any]:
        """Calculate average strain over the last N days."""
        cycles = self.get_cycles(days)
        if not cycles or "error" in cycles[0]:
            return {"error": "No cycle data available"}
        
        strains = [cycle.get('strain', 0) for cycle in cycles if cycle.get('strain') is not None]
        if not strains:
            return {"error": "No strain data available"}
        
        return {
            "average_strain": sum(strains) / len(strains),
            "days_analyzed": days,
            "samples": len(strains)
        }

# Initialize Whoop API client
whoop_api = WhoopAPI()

def handle_jsonrpc_message(message):
    """Handle JSON-RPC messages from the client."""
    print(f"Handling JSON-RPC message: {message}", file=sys.stderr)
    
    try:
        # Parse the message
        request = json.loads(message) if isinstance(message, str) else message
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Prepare the response structure
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }
        
        # Handle different methods
        if method == "initialize":
            print(f"Initializing with params: {params}", file=sys.stderr)
            response["result"] = {
                "capabilities": SERVER_CAPABILITIES
            }
        
        elif method == "getLatestCycle":
            print("Getting latest cycle data", file=sys.stderr)
            response["result"] = whoop_api.get_latest_cycle()
        
        elif method == "getAverageStrain":
            days = params.get("days", 7)
            print(f"Getting average strain for {days} days", file=sys.stderr)
            response["result"] = whoop_api.get_average_strain(days)
        
        elif method == "checkAuthStatus":
            print("Checking authentication status", file=sys.stderr)
            response["result"] = {
                "authenticated": whoop_api.client is not None,
                "message": "Successfully authenticated with Whoop" if whoop_api.client else "Not authenticated with Whoop"
            }
        
        elif method == "shutdown":
            print("Shutdown requested", file=sys.stderr)
            response["result"] = {"status": "shutting down"}
            # Return the response before shutting down
            return json.dumps(response), True
        
        else:
            print(f"Unknown method: {method}", file=sys.stderr)
            response["error"] = {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        
        return json.dumps(response), False
    
    except Exception as e:
        print(f"Error handling JSON-RPC message: {str(e)}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        return json.dumps(error_response), False

def handle_client(client_socket):
    """Handle a client connection."""
    print(f"Client connected: {client_socket.getpeername()}", file=sys.stderr)
    
    try:
        # Set a timeout for receiving data
        client_socket.settimeout(60)  # 60 seconds timeout
        
        # Buffer for incoming data
        buffer = b""
        
        while True:
            # Read data from the client
            data = client_socket.recv(4096)
            if not data:
                print("Client disconnected", file=sys.stderr)
                break
            
            # Add to buffer
            buffer += data
            
            # Try to parse complete messages
            try:
                # Decode and process the message
                message = buffer.decode('utf-8')
                print(f"Received message: {message}", file=sys.stderr)
                
                # Handle the JSON-RPC message
                response, should_shutdown = handle_jsonrpc_message(message)
                
                # Send the response back to the client
                print(f"Sending response: {response}", file=sys.stderr)
                client_socket.sendall(response.encode('utf-8'))
                
                # Clear the buffer after successful processing
                buffer = b""
                
                # Check if we should shutdown
                if should_shutdown:
                    print("Shutting down server as requested", file=sys.stderr)
                    break
            except json.JSONDecodeError:
                # Incomplete message, continue receiving
                print("Incomplete JSON message, continuing to receive", file=sys.stderr)
                continue
    
    except socket.timeout:
        print("Client connection timed out", file=sys.stderr)
    except Exception as e:
        print(f"Error handling client: {str(e)}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
    finally:
        # Close the client socket
        client_socket.close()
        print("Client connection closed", file=sys.stderr)

def run_server(port=8000):
    """Run the MCP server."""
    try:
        # Create a TCP/IP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Allow reuse of the address
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind the socket to the address
        server_address = ('127.0.0.1', port)
        print(f"Starting server on {server_address[0]}:{server_address[1]}", file=sys.stderr)
        server_socket.bind(server_address)
        
        # Listen for incoming connections
        server_socket.listen(5)
        print("Server is listening for connections", file=sys.stderr)
        
        while True:
            # Wait for a connection
            print("Waiting for a connection...", file=sys.stderr)
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}", file=sys.stderr)
            
            # Handle the client in a new thread
            client_thread = threading.Thread(target=handle_client, args=(client_socket,))
            client_thread.daemon = True
            client_thread.start()
    
    except KeyboardInterrupt:
        print("Server shutting down due to keyboard interrupt", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {str(e)}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
    finally:
        # Close the server socket
        server_socket.close()
        print("Server socket closed", file=sys.stderr)

def main():
    """Main entry point for the server."""
    try:
        print("In main() function", file=sys.stderr)
        logger.info("Starting Whoop MCP Server...")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Environment file path: {env_path}")
        
        if not whoop_api.client:
            print("ERROR: Not authenticated with Whoop", file=sys.stderr)
            logger.error("Not authenticated with Whoop. Please set WHOOP_EMAIL and WHOOP_PASSWORD in config/.env")
            logger.info("Server will continue running but authentication-required endpoints will fail")
        else:
            print("Successfully authenticated with Whoop", file=sys.stderr)
            logger.info("Successfully authenticated with Whoop")
        
        print("Starting MCP server...", file=sys.stderr)
        run_server(port=8000)
    except KeyboardInterrupt:
        print("Server shutting down due to keyboard interrupt", file=sys.stderr)
        logger.info("Server shutting down...")
    except Exception as e:
        print(f"ERROR: Server error: {str(e)}", file=sys.stderr)
        logger.error(f"Server error: {str(e)}", exc_info=True)
        print(traceback.format_exc(), file=sys.stderr)
        raise

if __name__ == "__main__":
    print("Script executed directly", file=sys.stderr)
    main() 