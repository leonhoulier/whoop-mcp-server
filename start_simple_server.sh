#!/bin/bash
# Script to start the Simple MCP server

# Change to the project directory
cd "$(dirname "$0")"

# Activate the virtual environment
source venv/bin/activate

# Print debug information
echo "Starting Simple MCP server..." >&2
echo "Current directory: $(pwd)" >&2
echo "Python executable: $(which python)" >&2

# Kill any existing server
pkill -f "python src/simple_mcp_server.py" || true

# Start the server with explicit stderr redirection
exec python src/simple_mcp_server.py 2>&1 