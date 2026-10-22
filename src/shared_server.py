"""Authenticated, stateless HTTP MCP for the shared health dashboard."""
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

import httpx
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from starlette.responses import JSONResponse

from shared_whoop import Vault, Whoop, WhoopError

Person = Literal["leon", "swastika"]
Limit = Annotated[int, Field(ge=1, le=25)]
Short = Annotated[str, Field(min_length=1, max_length=4096)]
Nonce = Annotated[str, Field(min_length=32, max_length=128)]
State = Annotated[str, Field(pattern=r"^[\w-]{8}$")]


def create_server(whoop, keys):
    if not keys or any(len(key) < 32 or role not in ("dashboard", "leon", "swastika") for key, role in keys.items()):
        raise RuntimeError("Configure strong MCP access keys before starting.")

    class Verifier:
        async def verify_token(self, token):
            for key, role in keys.items():
                if hmac.compare_digest(key, token):
                    return AccessToken(token=token, client_id=role, scopes=[role])
            return None

    # Provisioned service credentials only; this server does not advertise an
    # OAuth authorization server or dynamic registration it does not implement.
    mcp = FastMCP("WHOOP", json_response=True, stateless_http=True,
        token_verifier=Verifier(),
        auth=AuthSettings(issuer_url="https://fit.leonhoulier.com", resource_server_url=None),
        transport_security=TransportSecuritySettings(
            allowed_hosts=["fit.leonhoulier.com", "mcp.leonhoulier.com", "127.0.0.1:*", "localhost:*", "whoop-mcp:8003"],
            allowed_origins=["https://fit.leonhoulier.com"]),
        log_level="WARNING", max_request_body_size=65536)

    def permit(person, manage=False):
        auth = get_access_token()
        if not auth or ("dashboard" not in auth.scopes and (manage or person not in auth.scopes)):
            raise WhoopError("This connection cannot access that account or action.")

    @mcp.tool()
    async def check_auth_status(person: Person = "leon") -> dict:
        """Connection readiness. Never returns account tokens or personal profile fields."""
        permit(person)
        return whoop.status(person)

    @mcp.tool()
    async def begin_connection(person: Person, browser_nonce: Nonce) -> dict:
        """Dashboard only: begin WHOOP authorization bound to this browser."""
        permit(person, True)
        return whoop.begin(person, browser_nonce)

    @mcp.tool()
    async def finish_connection(state: State, code: Short, browser_nonce: Nonce) -> dict:
        """Dashboard only: finish a single-use authorization flow."""
        permit("leon", True)
        return await whoop.finish(state, code, browser_nonce)

    @mcp.tool()
    async def disconnect_account(person: Person) -> dict:
        """Dashboard only: remove this service's tokens, preserving other integrations."""
        permit(person, True)
        return await whoop.disconnect(person)

    @mcp.tool()
    async def get_health_snapshot(person: Person, start: str, end: str) -> dict:
        """Read complete paginated cycles, sleep, recovery and workouts, up to 100 days."""
        permit(person)
        try:
            first, last = (datetime.fromisoformat(value.replace("Z", "+00:00")) for value in (start, end))
            if not first.tzinfo or not last.tzinfo or not timedelta(0) < last - first <= timedelta(days=100):
                raise ValueError()
        except (ValueError, TypeError):
            raise WhoopError("Provide a valid date range of at most 100 days.") from None
        return await whoop.snapshot(person, start, end)

    def collection(name, path, description):
        async def read(person: Person = "leon", start: str | None = None, end: str | None = None, limit: Limit = 25, nextToken: Short | None = None) -> dict:
            permit(person)
            params = {k: v for k, v in {"start": start, "end": end, "limit": limit, "nextToken": nextToken}.items() if v is not None}
            return await whoop.read(person, path, params)
        mcp.add_tool(read, name=name, description=description)

    collection("get_cycles_data", "/cycle", "Physiological cycles; pass next_token back as nextToken for subsequent pages.")
    collection("get_recovery_data", "/recovery", "Recovery, HRV and resting heart rate, with pagination.")
    collection("get_sleep_data", "/activity/sleep", "Sleep stages and performance, with pagination.")
    collection("get_workout_data", "/activity/workout", "Workouts with pagination.")

    @mcp.tool()
    async def get_latest_cycle(person: Person = "leon") -> dict:
        permit(person)
        return await whoop.read(person, "/cycle", {"limit": 1})

    @mcp.tool()
    async def get_latest_sleep(person: Person = "leon") -> dict:
        permit(person)
        return await whoop.read(person, "/activity/sleep", {"limit": 1})

    @mcp.tool()
    async def get_sleep_for_cycle(cycle_id: Annotated[int, Field(gt=0)], person: Person = "leon") -> dict:
        permit(person)
        return await whoop.read(person, f"/cycle/{cycle_id}/sleep")

    @mcp.tool()
    async def get_workout_by_id(workout_id: UUID, person: Person = "leon") -> dict:
        permit(person)
        return await whoop.read(person, f"/activity/workout/{workout_id}")

    @mcp.tool()
    async def get_body_measurements(person: Person = "leon") -> dict:
        permit(person)
        return await whoop.read(person, "/user/measurement/body")

    @mcp.tool()
    async def get_recent_workouts(person: Person = "leon") -> dict:
        permit(person)
        now = datetime.now(timezone.utc)
        async with whoop.locks[person]:
            rows = await whoop.all_pages(person, "/activity/workout", (now - timedelta(days=7)).isoformat(), now.isoformat())
        return {"records": rows}

    @mcp.tool()
    async def get_average_strain(days: Annotated[int, Field(ge=1, le=30)] = 7, person: Person = "leon") -> dict:
        permit(person)
        now = datetime.now(timezone.utc)
        async with whoop.locks[person]:
            rows = await whoop.all_pages(person, "/cycle", (now - timedelta(days=days)).isoformat(), now.isoformat())
        scores = [r["score"]["strain"] for r in rows if r.get("score_state") == "SCORED" and isinstance(r.get("score", {}).get("strain"), (int, float))]
        return {"average_strain": sum(scores) / len(scores) if scores else None, "scored_cycles": len(scores), "days": days}

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request):
        return JSONResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})

    return mcp


def application():
    # Never load the historical committed mcp_config.json/config/tokens.json.
    directory = Path(os.environ.get("WHOOP_DATA_DIR", "/data"))
    config_path = Path(os.environ.get("WHOOP_CONFIG_FILE", str(directory / "config.json")))
    config = json.loads(config_path.read_text())
    if config.get("redirect_uri") != "https://fit.leonhoulier.com/api/whoop/callback":
        raise RuntimeError("Unexpected WHOOP callback URL.")
    client = httpx.AsyncClient(timeout=20, follow_redirects=False)
    whoop = Whoop(Vault(directory), config, client)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return create_server(whoop, config["access_keys"]).streamable_http_app()


def main():
    import uvicorn
    uvicorn.run(application(), host="0.0.0.0", port=8003, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
