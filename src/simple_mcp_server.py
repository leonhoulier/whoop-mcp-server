#!/usr/bin/env python3
import os
import sys
import json
import logging
import socket
import threading
import traceback
from typing import Dict, Any, Optional

# Configure logging to stderr (important for Claude Desktop)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("MCP-Server")

# Print debug information
logger.info("Starting Simple MCP Server...")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Script path: {os.path.abspath(__file__)}")

# Server capabilities
SERVER_CAPABILITIES = {
    "server": {
        "name": "Simple MCP Server",
        "version": "0.1.0",
        "description": "Minimal MCP server for testing"
    },
    "resources": [
        {
            "name": "test",
            "description": "Test resource"
        }
    ],
    "tools": [
        {
            "name": "echo",
            "description": "Echo back the input"
        }
    ]
}

class JsonRpcError(Exception):
    """JSON-RPC error with code and message."""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"JSON-RPC error {code}: {message}")

def create_response(request_id: Any, result: Any = None, error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a JSON-RPC response."""
    response = {
        "jsonrpc": "2.0",
        "id": request_id
    }
    
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
        
    return response

def handle_initialize(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle initialize request."""
    logger.info(f"Handling initialize with params: {params}")
    protocol_version = params.get("protocolVersion")
    logger.info(f"Protocol version: {protocol_version}")
    
    return {
        "capabilities": SERVER_CAPABILITIES
    }

def handle_echo(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle echo request."""
    logger.info(f"Handling echo with params: {params}")
    text = params.get("text", "No text provided")
    return {"text": f"Echo: {text}"}

def handle_jsonrpc_message(message_str: str) -> str:
    """Handle a JSON-RPC message and return the response."""
    logger.info(f"Received message: {message_str}")
    
    try:
        # Parse the message
        message = json.loads(message_str)
        
        # Extract request information
        jsonrpc = message.get("jsonrpc")
        if jsonrpc != "2.0":
            raise JsonRpcError(-32600, "Invalid Request: Not JSON-RPC 2.0")
            
        method = message.get("method")
        if not method:
            raise JsonRpcError(-32600, "Invalid Request: No method specified")
            
        params = message.get("params", {})
        request_id = message.get("id")
        
        # Handle methods
        if method == "initialize":
            result = handle_initialize(params)
            response = create_response(request_id, result)
        elif method == "echo":
            result = handle_echo(params)
            response = create_response(request_id, result)
        elif method == "shutdown":
            result = {"status": "shutting down"}
            response = create_response(request_id, result)
        else:
            raise JsonRpcError(-32601, f"Method not found: {method}")
            
    except JsonRpcError as e:
        logger.error(f"JSON-RPC error: {e}")
        response = create_response(
            request_id if 'request_id' in locals() else None,
            error={"code": e.code, "message": e.message, "data": e.data}
        )
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        response = create_response(
            None,
            error={"code": -32700, "message": "Parse error", "data": str(e)}
        )
    except Exception as e:
        logger.error(f"Internal error: {e}")
        logger.error(traceback.format_exc())
        response = create_response(
            request_id if 'request_id' in locals() else None,
            error={"code": -32603, "message": "Internal error", "data": str(e)}
        )
    
    # Convert response to string
    response_str = json.dumps(response)
    logger.info(f"Sending response: {response_str}")
    return response_str

def handle_client(client_socket: socket.socket) -> None:
    """Handle a client connection."""
    client_address = client_socket.getpeername()
    logger.info(f"Client connected: {client_address}")
    
    try:
        # Set a timeout for receiving data
        client_socket.settimeout(60)  # 60 seconds timeout
        
        # Buffer for incoming data
        buffer = b""
        
        while True:
            # Read data from the client
            data = client_socket.recv(4096)
            if not data:
                logger.info("Client disconnected")
                break
            
            # Add to buffer
            buffer += data
            
            # Try to parse complete messages
            try:
                # Decode the message
                message_str = buffer.decode('utf-8')
                
                # Handle the message
                response_str = handle_jsonrpc_message(message_str)
                
                # Send the response
                client_socket.sendall(response_str.encode('utf-8'))
                
                # Clear the buffer
                buffer = b""
                
                # Check if we should shutdown (this is a simple check)
                if '"method":"shutdown"' in message_str:
                    logger.info("Shutdown requested, closing connection")
                    break
                    
            except json.JSONDecodeError:
                # Incomplete message, continue receiving
                logger.debug("Incomplete JSON message, continuing to receive")
                continue
            except UnicodeDecodeError:
                # Invalid UTF-8, clear buffer and continue
                logger.error("Invalid UTF-8 in received data, clearing buffer")
                buffer = b""
                continue
    
    except socket.timeout:
        logger.warning("Client connection timed out")
    except ConnectionResetError:
        logger.warning("Connection reset by peer")
    except Exception as e:
        logger.error(f"Error handling client: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Close the client socket
        client_socket.close()
        logger.info("Client connection closed")

def run_server(host: str = '127.0.0.1', port: int = 8000) -> None:
    """Run the MCP server."""
    try:
        # Create a TCP/IP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Allow reuse of the address
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind the socket to the address
        server_address = (host, port)
        logger.info(f"Starting server on {host}:{port}")
        server_socket.bind(server_address)
        
        # Listen for incoming connections
        server_socket.listen(5)
        logger.info("Server is listening for connections")
        
        while True:
            # Wait for a connection
            logger.info("Waiting for a connection...")
            client_socket, client_address = server_socket.accept()
            logger.info(f"Connection from {client_address}")
            
            # Handle the client in a new thread
            client_thread = threading.Thread(target=handle_client, args=(client_socket,))
            client_thread.daemon = True
            client_thread.start()
    
    except KeyboardInterrupt:
        logger.info("Server shutting down due to keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Close the server socket
        server_socket.close()
        logger.info("Server socket closed")

if __name__ == "__main__":
    logger.info("Starting MCP server...")
    run_server() 