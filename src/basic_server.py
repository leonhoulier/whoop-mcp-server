#!/usr/bin/env python3
import os
import sys
import json
import logging
import socket
import threading
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("BasicServer")

# Print debug information
logger.info("Starting Basic Server...")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")

# Server capabilities
SERVER_CAPABILITIES = {
    "server": {
        "name": "Basic Server",
        "version": "0.1.0",
        "description": "Basic MCP server for testing"
    },
    "resources": [],
    "tools": []
}

def handle_initialize(request_id):
    """Handle initialize request."""
    logger.info("Handling initialize request")
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "capabilities": SERVER_CAPABILITIES
        }
    }

def handle_request(data):
    """Handle a JSON-RPC request."""
    try:
        request = json.loads(data)
        method = request.get("method")
        request_id = request.get("id")
        
        logger.info(f"Received request: {method} (id: {request_id})")
        
        if method == "initialize":
            return handle_initialize(request_id)
        else:
            logger.warning(f"Unknown method: {method}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        logger.error(traceback.format_exc())
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

def handle_client(client_socket):
    """Handle a client connection."""
    try:
        logger.info("Client connected")
        
        # Read data from the client
        data = client_socket.recv(4096)
        if data:
            logger.info(f"Received data: {data.decode('utf-8')}")
            
            # Handle the request
            response = handle_request(data.decode('utf-8'))
            
            # Send the response
            response_json = json.dumps(response)
            logger.info(f"Sending response: {response_json}")
            client_socket.sendall(response_json.encode('utf-8'))
        
    except Exception as e:
        logger.error(f"Error handling client: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Close the client socket
        client_socket.close()
        logger.info("Client connection closed")

def run_server(host='127.0.0.1', port=8000):
    """Run the server."""
    try:
        # Create a TCP/IP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Close the server socket
        server_socket.close()
        logger.info("Server socket closed")

if __name__ == "__main__":
    run_server() 