#!/bin/bash
# Script to start the Whoop MCP server

# Enable error tracing
set -x

# Change to the project directory
cd "$(dirname "$0")"

# Activate the virtual environment
source venv/bin/activate

# Print debug information
echo "Starting Whoop MCP server..." >&2
echo "Current directory: $(pwd)" >&2
echo "Python executable: $(which python)" >&2
echo "Uvicorn executable: $(which uvicorn)" >&2
echo "Python version: $(python --version)" >&2
echo "Environment variables:" >&2
env | grep -E "PYTHON|PATH" >&2

# Check if the .env file exists
if [ -f "config/.env" ]; then
  echo "Found .env file at $(pwd)/config/.env" >&2
else
  echo "ERROR: .env file not found at $(pwd)/config/.env" >&2
fi

# Start the server with explicit stderr redirection
exec python -m uvicorn src.whoop_server:app --host 127.0.0.1 --port 8000 2>&1 