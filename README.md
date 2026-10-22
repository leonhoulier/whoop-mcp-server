# WHOOP MCP Server

Authenticated WHOOP v2 MCP used by [Together](https://fit.leonhoulier.com). Separate connections for Leon and Swastika, encrypted token storage, serialized rotating refresh tokens and complete paginated health snapshots.

Inspired by [ctvidic](https://github.com/leonhoulier/whoop-mcp-server/commits?author=ctvidic)'s initial implementation. Maintained by Léon Houlier.

## Current service

- HTTP entry: `python src/shared_server.py`, or the Docker image. Python 3.11+.
- Public MCP path: `https://fit.leonhoulier.com/whoop/mcp`. Clients must send a provisioned `Authorization: Bearer …` header. No unauthenticated health reads, dynamic client registration or MCP OAuth login is provided.
- The dashboard service key manages both accounts. Separate read keys can be restricted to `leon` or `swastika`. All tools enforce this restriction, including explicit person parameters.
- Existing metric tool names remain. Collection tools accept `person`, `start`, `end`, `limit` and `nextToken`; their response includes WHOOP's `next_token`.
- `get_health_snapshot` retrieves all pages of cycles, sleep, recovery and workouts for up to 100 days. It fails without returning a partial snapshot if any page fails.
- `begin_connection`, `finish_connection` and `disconnect_account` require the dashboard key. Connection states expire after ten minutes and are single-use, bound to the initiating browser's nonce. The website callback also checks an HttpOnly browser cookie.
- Disconnect deletes this service's tokens. It does not revoke the whole WHOOP app, which may be used by the owner's existing daily brief. Users can revoke the app in WHOOP settings.

## Existing WHOOP app

Reuse the existing developer app; do not create another one. Add `https://fit.leonhoulier.com/api/whoop/callback` to its redirect URLs. Enable `read:profile`, `read:cycles`, `read:sleep`, `read:recovery`, `read:workout`, `read:body_measurement`; requests include `offline`.

Historical commits contain an exposed app secret and old tokens. Their removal from this branch does **not** revoke them or erase Git history. If rotating the app secret with WHOOP, update every existing consumer. No historical tokens or secret are imported by this service. The old public OAuth-config endpoint is disabled. Legacy scripts and backup source files are not included in the deployment image.

Place private configuration at `/var/lib/whoop-mcp/config.json`, mode 0600, owned by UID 1000; copy the shape of `config/shared.example.json`. Generate independent random 256-bit access keys and map each to `dashboard`, `leon` or `swastika` in `access_keys`. Keep configuration outside the checkout. Empty WHOOP client credentials allow infrastructure checks but cannot authorize users.

The data directory contains a private Fernet key and atomically replaced encrypted accounts. A process lock prevents two service instances from owning the same rotating tokens. Run one worker. Back up the entire directory, including its key, to private storage. Never copy another integration's refresh-token file here; each connection must authorize its own grant.

## Deploy

Create Docker network `together-whoop`, prepare the private directory, then build/start with `WHOOP_RELEASE=<tag> docker compose up -d --build`. Only port 8003 on loopback is published. The dashboard joins this network and calls `http://whoop-mcp:8003/mcp` with its service key. Nginx proxies the public MCP path with access logging disabled. `/health` contains no account information.

Configure the website offline using its `server/configure-whoop-mcp.ts` helper and private stdin JSON with `endpoint`, `token` and `ready`. Set ready only after the private WHOOP client credentials and callback are configured. Then each person connects their own account from Together's Connections page.

## Validation

`uv venv .venv && uv pip install --python .venv/bin/python -r requirements.lock pytest pytest-asyncio`

`.venv/bin/python -m pytest -q tests/test_shared.py`

Tests use temporary encrypted stores and mock WHOOP responses: account isolation, nonce/replay/expiry, duplicate account rejection, serialized refresh, pagination, disconnect and authenticated MCP protocol requests. Live WHOOP imports require configured app credentials and each person's consent; fixture tests do not establish those.

[WHOOP OAuth](https://developer.whoop.com/docs/developing/oauth/) · [WHOOP v2 API](https://developer.whoop.com/api/) · [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
