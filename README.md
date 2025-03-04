# Whoop MCP Server

A Model Context Protocol (MCP) server for integrating Whoop data with LLM applications.

## Features

- OAuth 2.0 authentication with Whoop API
- Fetch latest cycle data
- Calculate average strain over specified periods
- MCP-compliant resources and tools

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example environment file:
   ```bash
   cp config/.env.example config/.env
   ```
4. Register your application in the [Whoop Developer Portal](https://developer.whoop.com)
5. Update `config/.env` with your Whoop API credentials:
   - `WHOOP_CLIENT_ID`
   - `WHOOP_CLIENT_SECRET`
   - `WHOOP_REDIRECT_URI`

## Running the Server

```bash
python src/whoop_server.py
```

The server will start on `http://localhost:8000`.

## MCP Integration

Configure in your MCP client (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "whoop": {
      "command": "python",
      "args": ["src/whoop_server.py"]
    }
  }
}
```

## Available Resources

- `whoop://cycle/latest` - Get the latest cycle data

## Available Tools

- `get_average_strain(days: int)` - Calculate average strain over the last N days
- `authenticate_whoop(code: str)` - Authenticate with Whoop using an authorization code

## Authentication Flow

1. Register your application in the Whoop Developer Portal
2. Configure the redirect URI (default: `http://localhost:8000/callback`)
3. Use the authentication endpoint to get an authorization code
4. Call the `authenticate_whoop` tool with the received code

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License 