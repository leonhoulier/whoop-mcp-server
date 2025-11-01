#!/bin/bash
set -euo pipefail
cd /home/ubuntu/whoop-mcp-server
source venv/bin/activate

# Load environment variables from .env file
set -a
source config/.env
set +a

export MCP_SSE_PORT=8003
echo "🚀 Starting Whoop MCP SSE server with OAuth..."
python src/whoop_mcp_sse_server.py
