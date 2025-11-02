#!/bin/bash
set -euo pipefail
cd /home/ubuntu/whoop-mcp-server
source venv/bin/activate

# Load environment variables from .env file
set -a
source config/.env
set +a

export MCP_HTTP_PORT=8003
echo "🚀 Starting Whoop MCP Streamable HTTP server..."
python src/whoop_mcp_http_server.py
