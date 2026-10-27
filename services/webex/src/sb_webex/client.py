"""OAuth and JSON-RPC client for the hosted read-oriented Webex MCP.

The Cisco internal certificate chain is trusted through the operating-system
certificate store. Verification is never disabled.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import json
import logging
import secrets
import time
import urllib.parse
from pathlib import Path
from typing import Any

import httpx
import truststore

truststore.inject_into_ssl()

logger = logging.getLogger(__name__)

MCP_URL = "https://aicoding-mcp-webexapis.cisco.com/mcp/"
_METADATA_URL = "https://aicoding-mcp-webexapis.cisco.com/.well-known/oauth-authorization-server/mcp"
# Standard Webex REST API -- used only for the two read-only, single-resource
# lookups (me, one message-by-id) that the hosted MCP tool surface does not
# cleanly expose. Same bearer token as the hosted MCP; no separate auth.
WEBEX_API_BASE = "https://webexapis.com/v1"
_PARENT_LOOKUP_CACHE_SIZE = 500
READ_SCOPES = " ".join(
    [
        "meeting:schedules_read",
        "meeting:participants_read",
        "meeting:transcripts_read",
        # The server does not advertise a message-read scope. spark:all is
        # required to list spaces and messages. This client still refuses
        # every write-named tool.
        "spark:all",
    ]
)
_KEYRING_SERVICE = "sb"
_STATE_PATH = Path.home() / ".local/share/sb/webex-oauth-state.json"


class WebexAuthError(RuntimeError):
    pass


def _keyring_get(account: str) -> str | None:
    try:
        import keyring

        return keyring.get_password(_KEYRING_SERVICE, account)
    except Exception:
        return None


def _keyring_set(account: str, value: str) -> None:
    import keyring

    keyring.set_password(_KEYRING_SERVICE, account, value)


def authorization_metadata(timeout: float = 10.0) -> dict:
    response = httpx.get(_METADATA_URL, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def begin_login(redirect_uri: str, *, timeout: float = 15.0) -> str:
    """Register a public client if needed and return the authorize URL."""
    metadata = authorization_metadata(timeout=timeout)
    client_id = _keyring_get("webex.client_id")
    if not client_id:
        registered = httpx.post(
            metadata["registration_endpoint"],
            json={
                "client_name": "sb-core",
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
            timeout=timeout,
        )
        registered.raise_for_status()
        client_id = registered.json()["client_id"]
        _keyring_set("webex.client_id", client_id)

    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(24)
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(
        json.dumps(
            {
                "state": state,
                "verifier": verifier,
                "redirect_uri": redirect_uri,
                "expires_at": time.time() + 600,
            }
        ),
        encoding="utf-8",
    )
    _STATE_PATH.chmod(0o600)
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": READ_SCOPES,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{metadata['authorization_endpoint']}?{query}"


def finish_login(code: str, state: str, *, timeout: float = 15.0) -> None:
    """Exchange a callback code. The verifier never leaves this machine."""
    try:
        pending = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WebexAuthError("Webex sign-in expired. Start it again.") from exc
    if pending.get("state") != state or time.time() > float(
        pending.get("expires_at") or 0
    ):
        raise WebexAuthError("Webex sign-in state did not match.")
    metadata = authorization_metadata(timeout=timeout)
    client_id = _keyring_get("webex.client_id")
    if not client_id:
        raise WebexAuthError("Webex client registration is missing.")
    response = httpx.post(
        metadata["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": pending["redirect_uri"],
            "client_id": client_id,
            "code_verifier": pending["verifier"],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    _store_token(response.json())
    _STATE_PATH.unlink(missing_ok=True)


def _store_token(payload: dict) -> None:
    access = payload.get("access_token")
    if not access:
        raise WebexAuthError("Webex token response had no access token.")
    _keyring_set("webex.access_token", access)
    if payload.get("refresh_token"):
        _keyring_set("webex.refresh_token", payload["refresh_token"])
    _keyring_set(
        "webex.access_expires_at",
        str(time.time() + int(payload.get("expires_in") or 3600) - 60),
    )


def access_token(*, timeout: float = 15.0) -> str | None:
    expires = _keyring_get("webex.access_expires_at")
    current = _keyring_get("webex.access_token")
    if current and expires and time.time() < float(expires):
        return current
    refresh = _keyring_get("webex.refresh_token")
    client_id = _keyring_get("webex.client_id")
    if not refresh or not client_id:
        return current
    metadata = authorization_metadata(timeout=timeout)
    response = httpx.post(
        metadata["token_endpoint"],
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": client_id,
        },
        timeout=timeout,
    )
    if response.status_code != 200:
        return None
    _store_token(response.json())
    return _keyring_get("webex.access_token")


def authenticated() -> bool:
    return bool(
        _keyring_get("webex.refresh_token") or _keyring_get("webex.access_token")
    )


# ---------------------------------------------------------------------------
# Standard Webex REST lookups: me + single message by id
#
# These bypass the hosted MCP tool surface (which does not cleanly expose a
# single-resource "get message by id" or "who am I" call) and hit the
# standard Webex API directly with the same bearer token. Both are read-only
# GETs; neither is retried automatically -- a transient failure here must
# never fail the surrounding sync.
# ---------------------------------------------------------------------------


def _fetch_me(token: str, *, timeout: float = 15.0) -> dict | None:
    """Fetch {email, display_name} for the authenticated user, or None on
    any error (never raises)."""
    try:
        response = httpx.get(
            f"{WEBEX_API_BASE}/people/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("webex get_me failed: %s", type(exc).__name__)
        return None
    emails = data.get("emails") or []
    email = str(emails[0]) if emails else ""
    if not email:
        return None
    return {"email": email, "display_name": str(data.get("displayName") or "")}


def _fetch_message_uncached(token: str, message_id: str, *, timeout: float = 15.0) -> dict | None:
    """Fetch one message by id. Returns None on 404 or any other error."""
    try:
        response = httpx.get(
            f"{WEBEX_API_BASE}/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("webex get_message failed: %s", type(exc).__name__)
        return None
    return {
        "id": str(data.get("id") or message_id),
        "personEmail": str(data.get("personEmail") or ""),
        "personName": str(data.get("personDisplayName") or data.get("personEmail") or ""),
        "text": str(data.get("text") or ""),
    }


@functools.lru_cache(maxsize=_PARENT_LOOKUP_CACHE_SIZE)
def _fetch_message_by_hash(token_hash: str, message_id: str, token: str) -> dict | None:
    """LRU cache keyed on a token *hash* (not the raw token) + message id.

    The raw ``token`` is still passed through for the actual fetch, but it is
    excluded from the cache key by hashing it into ``token_hash`` upstream, so
    the secret is never retained as an ``lru_cache`` key. A token rotation
    changes the hash and therefore never serves a stale cross-account entry.
    """
    return _fetch_message_uncached(token, message_id)


def _fetch_message_cached(token: str, message_id: str) -> dict | None:
    """Bounded in-process cache (LRU, 500 entries) over ``_fetch_message_uncached``.

    The cache key is ``(sha256(token), message_id)`` so the bearer token is not
    held as a cache key. Not persisted between processes.
    """
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return _fetch_message_by_hash(token_hash, message_id, token)


# Expose the underlying LRU controls on the public wrapper so callers (and
# tests) can clear or inspect the cache without reaching the hashed inner fn.
_fetch_message_cached.cache_clear = _fetch_message_by_hash.cache_clear  # type: ignore[attr-defined]
_fetch_message_cached.cache_info = _fetch_message_by_hash.cache_info  # type: ignore[attr-defined]


class McpClient:
    """Minimal Streamable HTTP client. It never logs message bodies or tokens."""

    def __init__(self, token: str, url: str = MCP_URL) -> None:
        self._token = token
        self._url = url
        self._session: str | None = None

    def _rpc(
        self, method: str, params: dict | None = None, *, notify: bool = False
    ) -> Any:
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if not notify:
            body["id"] = 1
        if params is not None:
            body["params"] = params
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        response = httpx.post(self._url, headers=headers, json=body, timeout=30.0)
        if response.status_code == 401:
            raise WebexAuthError("Webex MCP rejected the sign-in. Sign in again.")
        response.raise_for_status()
        self._session = response.headers.get("mcp-session-id") or self._session
        text = response.text.strip()
        if not text:
            return None
        if text.startswith("{"):
            message = response.json()
        else:
            data = [
                line.split(":", 1)[1].strip()
                for line in text.splitlines()
                if line.startswith("data:")
            ]
            message = json.loads(data[-1])
        if isinstance(message, dict) and message.get("error"):
            raise WebexAuthError(
                str(message["error"].get("message") or "Webex MCP error")
            )
        return None if notify else message.get("result")

    def list_tools(self) -> list[dict]:
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "sb-core", "version": "0.1.0"},
            },
        )
        self._rpc("notifications/initialized", notify=True)
        result = self._rpc("tools/list") or {}
        return list(result.get("tools") or [])

    def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        result = (
            self._rpc(
                "tools/call",
                {"name": name, "arguments": arguments or {}},
            )
            or {}
        )
        structured = result.get("structuredContent")
        if isinstance(structured, dict) and "result" in structured:
            return structured["result"]
        if structured is not None:
            return structured
        content = result.get("content") or []
        if content and isinstance(content[0], dict) and content[0].get("text"):
            try:
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                return {"text": content[0]["text"][:180]}
        return {}

    def get_me(self) -> dict | None:
        """Return ``{email, display_name}`` for the authenticated user via
        the standard Webex REST API. None on any error; never raises."""
        return _fetch_me(self._token)

    def get_message(self, message_id: str) -> dict | None:
        """Return ``{id, personEmail, personName, text}`` for one message,
        via a bounded in-process LRU cache. None on 404 or any other error;
        never raises."""
        return _fetch_message_cached(self._token, message_id)
