"""WHOOP v2 account owner. One process owns each rotating refresh token."""
import asyncio
import fcntl
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet

PEOPLE = ("leon", "swastika")
SCOPES = "offline read:profile read:cycles read:sleep read:recovery read:workout read:body_measurement"
API = "https://api.prod.whoop.com/developer/v2"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"


class WhoopError(Exception):
    """Only safe, constant messages may cross the MCP boundary."""


class Vault:
    def __init__(self, directory: Path):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
        self.lock = open(directory / "owner.lock", "a+")
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        key = directory / "vault.key"
        if not key.exists():
            fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(Fernet.generate_key())
        os.chmod(key, 0o600)
        self.cipher = Fernet(key.read_bytes())
        self.path = directory / "accounts.enc"
        self.accounts = json.loads(self.cipher.decrypt(self.path.read_bytes())) if self.path.exists() else {}

    def save(self, person, value):
        updated = {**self.accounts, person: value}
        temporary = self.path.with_suffix(".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(self.cipher.encrypt(json.dumps(updated).encode()))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        directory = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self.accounts = updated


class Whoop:
    def __init__(self, vault, config, client):
        self.vault, self.config, self.client = vault, config, client
        self.locks = {person: asyncio.Lock() for person in PEOPLE}
        self.assignment = asyncio.Lock()
        self.pending = {}

    def configured(self):
        return bool(self.config.get("client_id") and self.config.get("client_secret"))

    def status(self, person):
        account = self.vault.accounts.get(person, {})
        return {"person": person, "configured": self.configured(), "connected": bool(account.get("tokens")), "accountId": account.get("accountId")}

    def begin(self, person, nonce):
        if not self.configured():
            raise WhoopError("WHOOP application setup is incomplete.")
        self.pending = {k: v for k, v in self.pending.items() if v["expires"] > time.time() and v["person"] != person}
        state = secrets.token_urlsafe(6)  # WHOOP requires exactly eight characters.
        while state in self.pending:
            state = secrets.token_urlsafe(6)
        self.pending[state] = {"person": person, "nonce": nonce, "expires": time.time() + 600}
        query = urlencode({"response_type": "code", "client_id": self.config["client_id"], "redirect_uri": self.config["redirect_uri"], "scope": SCOPES, "state": state})
        return {"url": AUTH_URL + "?" + query, "state": state}

    async def exchange(self, data):
        try:
            response = await self.client.post(TOKEN_URL, data={**data, "client_id": self.config["client_id"], "client_secret": self.config["client_secret"]})
            if response.status_code != 200:
                raise WhoopError("WHOOP authorization failed. Reconnect this account.")
            tokens = response.json()
            if not all(isinstance(tokens.get(k), str) and tokens[k] for k in ("access_token", "refresh_token")) or str(tokens.get("token_type", "")).lower() != "bearer" or not isinstance(tokens.get("expires_in"), (int, float)) or tokens["expires_in"] <= 0:
                raise WhoopError("WHOOP returned invalid credentials.")
            # Persist rotated credentials before checking scopes: old refresh tokens are spent.
            return {"tokens": tokens, "expiresAt": time.time() + tokens["expires_in"]}
        except (httpx.HTTPError, ValueError, KeyError):
            raise WhoopError("WHOOP authorization is unavailable.") from None

    async def finish(self, state, code, nonce):
        flow = self.pending.get(state)
        if not flow or flow["expires"] <= time.time() or not hmac.compare_digest(flow["nonce"], nonce):
            raise WhoopError("Connection expired or browser changed.")
        del self.pending[state]  # Consume before any network request; never replay a code.
        person = flow["person"]
        async with self.assignment, self.locks[person]:
            fresh = await self.exchange({"grant_type": "authorization_code", "code": code, "redirect_uri": self.config["redirect_uri"]})
            scope = fresh["tokens"].get("scope")
            if scope and not set(SCOPES.split()).issubset(scope.split()):
                raise WhoopError("WHOOP did not grant all requested permissions.")
            try:
                response = await self.client.get(API + "/user/profile/basic", headers={"Authorization": "Bearer " + fresh["tokens"]["access_token"]})
                profile = response.json() if response.status_code == 200 else {}
                if type(profile.get("user_id")) is not int:
                    raise WhoopError("Could not confirm the WHOOP account.")
            except (httpx.HTTPError, ValueError):
                raise WhoopError("Could not confirm the WHOOP account.") from None
            account_id = str(profile["user_id"])
            if any(p != person and a.get("accountId") == account_id for p, a in self.vault.accounts.items()):
                raise WhoopError("This WHOOP account belongs to the other person.")
            previous = self.vault.accounts.get(person, {})
            if previous.get("tokens") and previous.get("accountId") != account_id:
                raise WhoopError("Disconnect the previous account first.")
            self.vault.save(person, {**fresh, "accountId": account_id})
            return {"person": person, "accountId": account_id}

    async def access(self, person, force=False):
        account = self.vault.accounts.get(person, {})
        if not account.get("tokens"):
            raise WhoopError("Connect this WHOOP account first.")
        if force or account.get("expiresAt", 0) < time.time() + 60:
            fresh = await self.exchange({"grant_type": "refresh_token", "refresh_token": account["tokens"]["refresh_token"], "scope": "offline"})
            self.vault.save(person, {**account, **fresh})
            account = self.vault.accounts[person]
        return account["tokens"]["access_token"]

    async def _request(self, person, path, params=None):
        for attempt in range(2):
            token = await self.access(person, force=attempt == 1)
            try:
                response = await self.client.get(API + path, params=params, headers={"Authorization": "Bearer " + token})
                if response.status_code == 401 and attempt == 0:
                    continue
                if response.status_code != 200:
                    raise WhoopError("WHOOP rate limit reached." if response.status_code == 429 else "WHOOP could not return this data.")
                return response.json()
            except (httpx.HTTPError, ValueError):
                raise WhoopError("WHOOP is unavailable. Try again later.") from None

    async def read(self, person, path, params=None):
        async with self.locks[person]:
            return await self._request(person, path, params)

    async def all_pages(self, person, path, start, end):
        rows, seen, next_token = [], set(), None
        for _ in range(100):
            params = {"start": start, "end": end, "limit": 25}
            if next_token:
                params["nextToken"] = next_token
            page = await self._request(person, path, params)
            if not isinstance(page.get("records"), list):
                raise WhoopError("Invalid WHOOP response.")
            rows.extend(page["records"])
            next_token = page.get("next_token")
            if next_token in (None, ""):
                return rows
            if not isinstance(next_token, str) or next_token in seen:
                raise WhoopError("Invalid WHOOP pagination.")
            seen.add(next_token)
        raise WhoopError("WHOOP page limit reached.")

    async def snapshot(self, person, start, end):
        # A failed/partial download is never presented as a complete refresh.
        async with self.locks[person]:
            result = {}
            for metric, path in {"cycles": "/cycle", "sleep": "/activity/sleep", "recovery": "/recovery", "workouts": "/activity/workout"}.items():
                result[metric] = await self.all_pages(person, path, start, end)
            return {**result, "accountId": self.vault.accounts[person]["accountId"]}

    async def disconnect(self, person):
        async with self.locks[person]:
            # Disconnect locally; revoking the WHOOP app would also break the user's
            # existing daily brief, which has its own separate authorization grant.
            account = self.vault.accounts.get(person, {})
            self.vault.save(person, {"accountId": account.get("accountId")})
            self.pending = {k: v for k, v in self.pending.items() if v["person"] != person}
            return {"revoked": False, "disconnected": True}
