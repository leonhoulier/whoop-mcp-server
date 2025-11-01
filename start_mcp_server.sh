#!/bin/bash
cd /home/ubuntu/whoop-mcp-server
source venv/bin/activate

# Load environment variables from .env file
set -a
source config/.env
set +a

echo "🚀 Starting Whoop MCP Server with OAuth support..."
echo "📋 MCP Configuration:"
echo "  - Server: whoop-mcp-server"
echo "  - Version: 2.0.0"
echo "  - OAuth: Enabled"
echo "  - Endpoints: Recovery, Cycles, Strain, Auth Status"
echo ""
echo "🔗 For agent builders:"
echo "  - MCP Server URL: https://mcp.leonhoulier.com/whoop/mcp"
echo "  - OAuth Config: Available at /whoop/oauth-config"
echo ""

python src/whoop_mcp_server.py
