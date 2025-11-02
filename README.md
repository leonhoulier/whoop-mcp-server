# Whoop MCP Server

A Model Context Protocol (MCP) server that provides comprehensive access to the Whoop API. This server allows language models and applications to query cycles, recovery, strain, workout, and sleep data from the Whoop API with automatic token refresh and long-term authentication.

> **Note:** This project was inspired by the work of [ctvidic](https://github.com/leonhoulier/whoop-mcp-server/commits?author=ctvidic). Special thanks for the initial implementation.

## Prerequisites

### Whoop Developer Account

To use this server, you'll need:

1. **A Whoop Developer Account**: Sign up at [https://developer-dashboard.whoop.com](https://developer-dashboard.whoop.com)
2. **Create an App**: After creating your account, create a new application in the developer dashboard
3. **Configure OAuth Settings**:
   - Set your redirect URI (e.g., `https://your-domain.com/whoop/callback`)
   - Copy your Client ID and Client Secret
   - Note: Request the `offline` scope to enable refresh tokens for long-term authentication

## Features

- **Automatic Token Refresh**: Tokens refresh automatically before expiration (no manual re-authentication needed)
- **OAuth 2.0 with PKCE**: Secure authentication flow
- **Offline Scope Support**: Long-term access with refresh tokens
- **Comprehensive API Access**: All Whoop v2 API endpoints
- **Streamable HTTP Server**: Compatible with MCP clients via HTTP

## Available Tools

### Recovery Data
* `get_recovery_data`: Get recovery data including recovery score, HRV, resting heart rate, SpO2, and skin temperature

### Cycle Data
* `get_cycles_data`: Get physiological cycle data including strain, calories, and heart rate metrics
* `get_latest_cycle`: Get the most recent cycle data
* `get_average_strain`: Calculate average strain over a specified number of days

### Sleep Data
* `get_sleep_data`: Get sleep data including sleep stages, performance %, quality score, respiratory rate, and efficiency
* `get_sleep_for_cycle`: Get sleep data for a specific cycle by cycle ID
* `get_latest_sleep`: Get the most recent sleep data

### Workout Data
* `get_workout_data`: Get workout data including sport, strain score, heart rate zones, calories, and GPS data
* `get_workout_by_id`: Get specific workout by workout ID (UUID)
* `get_recent_workouts`: Get recent workouts from the last 7 days

### Body Measurements
* `get_body_measurements`: Get user body measurements including height, weight, and max heart rate

### Authentication
* `check_auth_status`: Check authentication status and get user profile

## Installation

### Prerequisites

* Python 3.12+
* Whoop Developer Account and OAuth credentials ([Get them here](https://developer-dashboard.whoop.com))
* Nginx (for production deployment)
* PM2 (for process management, optional)

### Local Setup

1. Clone this repository:
```bash
git clone https://github.com/leonhoulier/whoop-mcp-server.git
cd whoop-mcp-server
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp config/.env.example config/.env
nano config/.env
```

Add your Whoop OAuth credentials:
```env
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret
WHOOP_REDIRECT_URI=https://your-domain.com/whoop/callback
```

5. Authenticate with Whoop:
```bash
./scripts/authenticate_whoop.sh
```

Or visit the re-authentication endpoint after starting the server:
```
https://your-domain.com/whoop/reauth
```

Follow the OAuth flow to authorize your application. Tokens (including refresh tokens) will be saved automatically with expiration tracking.

## Deployment

### Production Setup with Nginx and PM2

This server is designed to run as a streamable HTTP MCP server behind Nginx.

#### 1. Start the MCP Server

The server runs on port 8003 by default:
```bash
./start_whoop_mcp_http.sh
```

Or manually:
```bash
cd /path/to/whoop-mcp-server
source venv/bin/activate
export MCP_HTTP_PORT=8003
python src/whoop_mcp_http_server.py
```

#### 2. Configure PM2 (Recommended)

Install PM2:
```bash
npm install -g pm2
```

Add the process to PM2:
```bash
pm2 start start_whoop_mcp_http.sh --name whoop-mcp-http
pm2 save
pm2 startup
```

#### 3. Configure Nginx

Add to your Nginx configuration (`/etc/nginx/sites-available/mcp.example.com`):

```nginx
server {
    listen 443 ssl http2;
    server_name mcp.example.com;

    ssl_certificate /etc/letsencrypt/live/mcp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.example.com/privkey.pem;

    # Whoop MCP Server - Streamable HTTP
    location /whoop/mcp {
        proxy_pass http://localhost:8003/mcp;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Accept "application/json, text/event-stream";
        proxy_buffering off;
    }

    # Whoop OAuth Callback (auto-exchanges tokens)
    location /whoop/callback {
        proxy_pass http://localhost:8003/callback;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Whoop Re-authentication Endpoint
    location /whoop/reauth {
        proxy_pass http://localhost:8003/reauth;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health Check
    location /whoop/health {
        proxy_pass http://localhost:8003/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Reload Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Usage with Cursor / Claude Desktop

Add to your Cursor or Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "whoop-mcp": {
      "url": "https://your-domain.com/whoop/mcp"
    }
  }
}
```

## Authentication

Whoop MCP uses OAuth 2.0 with PKCE for secure authentication. The server includes:

* **Automatic Token Refresh**: Access tokens refresh automatically before expiration (within 5 minutes of expiry)
* **Refresh Token Support**: Long-term authentication with the `offline` scope
* **Proactive Refresh**: Tokens are refreshed automatically, eliminating manual re-authentication
* **Re-authentication Endpoint**: Easy re-auth at `/whoop/reauth`
* **Auto Token Exchange**: OAuth callback automatically exchanges authorization codes for tokens

### Getting OAuth Credentials

1. Create a Whoop Developer account at [https://developer-dashboard.whoop.com](https://developer-dashboard.whoop.com)
2. Register a new application in the developer dashboard
3. Configure redirect URI: `https://your-domain.com/whoop/callback`
4. Copy Client ID and Client Secret to your `.env` file
5. **Important**: Ensure the `offline` scope is requested to receive refresh tokens

## Environment Variables

Required environment variables:

* `WHOOP_CLIENT_ID`: Your Whoop OAuth Client ID
* `WHOOP_CLIENT_SECRET`: Your Whoop OAuth Client Secret
* `WHOOP_REDIRECT_URI`: Your OAuth callback URL
* `MCP_HTTP_PORT`: Port for MCP HTTP server (default: 8003)
* `WHOOP_DOCS_PORT`: Port for documentation server (default: 8005)

## Project Structure

```
whoop-mcp-server/
├── src/
│   ├── whoop_mcp_server.py           # Core MCP server implementation
│   ├── whoop_mcp_http_server.py      # Streamable HTTP server
│   ├── whoop_mcp_sse_server.py       # Legacy SSE server
│   └── ...
├── config/
│   ├── .env.example                  # Environment variables template
│   └── tokens.json                   # Stored OAuth tokens (gitignored)
├── scripts/
│   ├── authenticate_whoop.sh         # OAuth authentication script
│   └── authenticate_whoop.py         # OAuth helper Python script
├── storage/                          # OAuth storage
├── whoop_docs_server.py              # Documentation server
├── start_whoop_mcp_http.sh           # MCP HTTP startup script
├── start_whoop_docs.sh               # Docs server startup script
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

## API Reference

The server uses the Whoop API v2. See the [Whoop Developer Documentation](https://developer.whoop.com/docs/developing/oauth) for full API specifications.

## Troubleshooting

### Token Expiration

With refresh tokens configured, you should **not** need to manually re-authenticate. However, if you receive authentication errors:

1. Visit `https://your-domain.com/whoop/reauth`
2. Re-authorize with Whoop
3. The new token (including refresh token) will be saved automatically

### Server Not Starting

Check PM2 logs:
```bash
pm2 logs whoop-mcp-http
```

Verify port is available:
```bash
lsof -i :8003
```

### 404 Errors

Ensure Nginx configuration matches your actual port and endpoints. The server exposes:

* `/mcp` - Main MCP endpoint
* `/health` - Health check
* `/reauth` - Re-authentication
* `/callback` - OAuth callback (auto-exchanges tokens)

### No Refresh Token

If you're not receiving refresh tokens:
1. Ensure `offline` scope is included in OAuth requests
2. Verify your app is approved for offline access in the Whoop developer dashboard
3. Check server logs for scope information

## License

MIT License - see LICENSE file for details.

## Author

Léon Houlier - [leonhoulier.com](https://leonhoulier.com)

## Acknowledgments

This project was inspired by the work of [ctvidic](https://github.com/leonhoulier/whoop-mcp-server/commits?author=ctvidic). Built with the Model Context Protocol SDK and the Whoop API.
