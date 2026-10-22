import asyncio
import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shared_whoop import API, SCOPES, Vault, Whoop, WhoopError
from shared_server import create_server


@pytest.fixture
def setup(tmp_path):
    requests = []
    def upstream(request):
        requests.append(request)
        if request.url.path.endswith("/token"):
            body = parse_qs(request.content.decode())
            source = body.get("code", body.get("refresh_token"))[0]
            person = "swastika" if "swastika" in source else "leon"
            return httpx.Response(200, json={"access_token": person, "refresh_token": person + "-rotated", "token_type": "bearer", "expires_in": 3600, "scope": SCOPES})
        person = request.headers["authorization"].split()[-1]
        if request.url.path.endswith("/profile/basic"):
            return httpx.Response(200, json={"user_id": 2 if person == "swastika" else 1})
        return httpx.Response(200, json={"records": [{"owner": person, "page": request.url.params.get("nextToken", "first")}], "next_token": None if request.url.params.get("nextToken") else "page-two"})
    vault = Vault(tmp_path)
    config = {"client_id": "test-client", "client_secret": "test-secret", "redirect_uri": "https://fit.leonhoulier.com/api/whoop/callback"}
    whoop = Whoop(vault, config, httpx.AsyncClient(transport=httpx.MockTransport(upstream)))
    yield whoop, requests
    vault.lock.close()


async def connect(whoop, person, code=None):
    flow = whoop.begin(person, "n" * 43)
    return await whoop.finish(flow["state"], code or person, "n" * 43)


@pytest.mark.asyncio
async def test_state_nonce_expiration_replay_and_duplicate_account(setup):
    whoop, requests = setup
    flow = whoop.begin("leon", "n" * 43)
    assert len(flow["state"]) == 8
    with pytest.raises(WhoopError):
        await whoop.finish(flow["state"], "leon", "wrong")
    assert requests == []
    await whoop.finish(flow["state"], "leon", "n" * 43)
    with pytest.raises(WhoopError):
        await whoop.finish(flow["state"], "leon", "n" * 43)
    with pytest.raises(WhoopError, match="other person"):
        await connect(whoop, "swastika", "leon")
    assert not whoop.status("swastika")["connected"]
    flow = whoop.begin("swastika", "n" * 43)
    whoop.pending[flow["state"]]["expires"] = 0
    with pytest.raises(WhoopError):
        await whoop.finish(flow["state"], "swastika", "n" * 43)


@pytest.mark.asyncio
async def test_separate_accounts_serialized_refresh_and_encrypted_atomic_persistence(setup):
    whoop, requests = setup
    await connect(whoop, "leon")
    await connect(whoop, "swastika")
    whoop.vault.save("leon", {**whoop.vault.accounts["leon"], "expiresAt": 0})
    before = sum(r.url.path.endswith("/token") for r in requests)
    results = await asyncio.gather(*(whoop.read("leon", "/cycle") for _ in range(4)))
    assert all(r["records"][0]["owner"] == "leon" for r in results)
    assert sum(r.url.path.endswith("/token") for r in requests) == before + 1
    assert (await whoop.read("swastika", "/cycle"))["records"][0]["owner"] == "swastika"
    assert b"leon-rotated" not in whoop.vault.path.read_bytes()
    assert whoop.vault.path.stat().st_mode & 0o777 == 0o600
    assert json.loads(whoop.vault.cipher.decrypt(whoop.vault.path.read_bytes()))["leon"]["tokens"]["refresh_token"] == "leon-rotated"
    with pytest.raises(BlockingIOError):
        Vault(whoop.vault.path.parent)


@pytest.mark.asyncio
async def test_snapshot_paginates_every_metric_and_refuses_repeated_cursor(setup):
    whoop, _ = setup
    await connect(whoop, "leon")
    result = await whoop.snapshot("leon", "2026-10-01T00:00:00Z", "2026-10-22T00:00:00Z")
    assert result["accountId"] == "1"
    assert all(len(result[k]) == 2 for k in ("cycles", "sleep", "recovery", "workouts"))
    whoop.client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"records": [], "next_token": "repeat"})))
    with pytest.raises(WhoopError, match="pagination"):
        await whoop.snapshot("leon", "2026-10-01T00:00:00Z", "2026-10-22T00:00:00Z")


@pytest.mark.asyncio
async def test_disconnect_invalidates_pending_and_preserves_other_account(setup):
    whoop, requests = setup
    await connect(whoop, "leon")
    await connect(whoop, "swastika")
    flow = whoop.begin("leon", "n" * 43)
    assert (await whoop.disconnect("leon"))["disconnected"]
    assert not whoop.status("leon")["connected"]
    assert whoop.status("swastika")["connected"]
    assert not any(r.method == "DELETE" for r in requests)
    with pytest.raises(WhoopError):
        await whoop.finish(flow["state"], "leon", "n" * 43)


def test_real_mcp_protocol_requires_auth_and_enforces_profile_permissions(setup):
    whoop, requests = setup
    server = create_server(whoop, {"d" * 43: "dashboard", "l" * 43: "leon"})
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    def rpc(client, name, args, token="d" * 43):
        return client.post("/mcp", headers={**headers, "Authorization": "Bearer " + token}, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})
    def data(result):
        return result.get("structuredContent") or json.loads(result["content"][0]["text"])
    with TestClient(server.streamable_http_app(), base_url="http://localhost:8003") as client:
        assert client.post("/mcp", headers=headers, json={}).status_code == 401
        assert rpc(client, "check_auth_status", {}, "bad").status_code == 401
        initialized = client.post("/mcp", headers={**headers, "Authorization": "Bearer " + "d" * 43}, json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}})
        assert initialized.status_code == 200
        assert data(rpc(client, "check_auth_status", {}, "l" * 43).json()["result"])["person"] == "leon"
        for name, args in (("check_auth_status", {"person": "swastika"}), ("begin_connection", {"person": "leon", "browser_nonce": "n" * 43})):
            assert rpc(client, name, args, "l" * 43).json()["result"]["isError"]
        assert requests == []
        flow = data(rpc(client, "begin_connection", {"person": "leon", "browser_nonce": "n" * 43}).json()["result"])
        connected = rpc(client, "finish_connection", {"state": flow["state"], "code": "leon", "browser_nonce": "n" * 43}).json()["result"]
        assert data(connected)["accountId"] == "1"
        assert "access_token" not in json.dumps(connected)
        assert rpc(client, "get_cycles_data", {"person": "leon", "limit": 26}).json()["result"]["isError"]
        assert rpc(client, "get_health_snapshot", {"person": "leon", "start": "2020-01-01T00:00:00Z", "end": "2026-10-22T00:00:00Z"}).json()["result"]["isError"]
        assert client.get("/health").json() == {"status": "ok"}
