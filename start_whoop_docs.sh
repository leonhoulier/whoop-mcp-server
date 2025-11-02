#!/bin/bash
# Startup script for Whoop MCP Documentation Server

cd /home/ubuntu/whoop-mcp-server
source venv/bin/activate

# Run the documentation server on port 8005
export WHOOP_DOCS_PORT=8005
python whoop_docs_server.py
