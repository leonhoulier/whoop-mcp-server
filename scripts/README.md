# Whoop Authentication Scripts

## Quick Start

To re-authenticate your Whoop MCP server:

```bash
cd /home/ubuntu/whoop-mcp-server
./scripts/authenticate_whoop.sh
```

Or run the Python script directly:

```bash
cd /home/ubuntu/whoop-mcp-server
source venv/bin/activate
source config/.env
python3 scripts/authenticate_whoop.py
```

## What it does

1. Generates an OAuth authorization URL
2. Opens the URL in your browser (you'll need to copy/paste it)
3. After authorizing, you'll be redirected to the callback URL
4. Paste the full callback URL back into the script
5. The script exchanges the authorization code for access/refresh tokens
6. Saves tokens to `config/tokens.json`

## Troubleshooting

- **Token expired**: Run this script to get a new token
- **Redirect URI mismatch**: Make sure `WHOOP_REDIRECT_URI` in `.env` matches your Whoop app settings
- **Invalid callback URL**: Copy the ENTIRE URL from your browser, including all query parameters

## Files

- `authenticate_whoop.py` - Main authentication script
- `authenticate_whoop.sh` - Shell wrapper for easy execution
