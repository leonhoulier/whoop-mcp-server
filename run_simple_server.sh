#!/bin/bash
# Script to start the Simple MCP server

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script directory: $SCRIPT_DIR" >&2

# Change to the project directory
cd "$SCRIPT_DIR"
echo "Changed to directory: $(pwd)" >&2

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"
echo "Activated virtual environment" >&2

# Print debug information
echo "Starting Simple MCP server..." >&2
echo "Current directory: $(pwd)" >&2
echo "Python executable: $(which python)" >&2
echo "Python version: $(python --version)" >&2

# Kill any existing server processes
pkill -f "python $SCRIPT_DIR/src/simple_mcp_server.py" || true
echo "Killed any existing server processes" >&2

# Start the server with absolute path
echo "Starting server with command: python $SCRIPT_DIR/src/simple_mcp_server.py" >&2
exec python "$SCRIPT_DIR/src/simple_mcp_server.py" 