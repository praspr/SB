"""Build the Cursor session cookie from the local Cursor desktop app's sqlite store.

Ports the logic from ``web/vite/cursor-auth.ts`` to pure Python (stdlib only).
The access token and cookie value are never logged -- only the (non-secret)
userId is logged, matching the Node implementation.
"""

from __future__ import annotations

import base64
import json
import logging
import sqlite3
import time
import urllib.parse
from pathlib import Path

logger = logging.getLogger(__name__)

_CURSOR_DB_PATH = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Cursor"
    / "User"
    / "globalStorage"
    / "state.vscdb"
)

_CACHE_TTL_SECONDS = 5 * 60

_cached_cookie: str | None = None
_cached_at: float = 0.0
_logged_once = False


def _read_access_token(db_path: Path) -> str | None:
    """Read the Cursor access token from the sqlite state DB, read-only."""
    if not db_path.exists():
        logger.warning(
            "[cursor-proxy] could not build cookie: state.vscdb not found at %s",
            db_path,
        )
        return None
    try:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            row = conn.execute(
                "SELECT value FROM ItemTable WHERE key = 'cursorAuth/accessToken'"
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 — fail soft, never raise
        logger.warning("[cursor-proxy] could not build cookie: %s", exc)
        return None


def _decode_jwt_sub(jwt: str) -> str | None:
    """Decode the ``sub`` claim from a JWT's base64url payload segment."""
    try:
        parts = jwt.split(".")
        if len(parts) < 2:
            return None
        payload_segment = parts[1]
        padding = "=" * (-len(payload_segment) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(payload_segment + padding).decode("utf-8")
        )
        sub = payload.get("sub")
        return sub if isinstance(sub, str) else None
    except Exception as exc:  # noqa: BLE001 — fail soft, never raise
        logger.warning("[cursor-proxy] could not build cookie: %s", exc)
        return None


def _build_cookie_header(db_path: Path) -> str | None:
    global _logged_once

    token = _read_access_token(db_path)
    if not token:
        return None

    sub = _decode_jwt_sub(token)
    if not sub:
        logger.warning("[cursor-proxy] could not build cookie: could not decode JWT sub")
        return None

    user_id = sub[len("auth0|") :] if sub.startswith("auth0|") else sub
    cookie_value = f"{user_id}::{token}"
    encoded = urllib.parse.quote(cookie_value, safe="")

    if not _logged_once:
        logger.info("[cursor-proxy] cookie built for user: %s", user_id)
        _logged_once = True

    return f"WorkosCursorSessionToken={encoded}"


def get_cursor_cookie(db_path: Path | None = None, use_cache: bool = True) -> str | None:
    """Return a cached (5 min TTL) ``Cookie`` header value for cursor.com, or None.

    Never raises; any failure to read/decode the local Cursor auth state
    results in ``None`` so the caller can forward the request unauthenticated.
    ``use_cache=False`` bypasses the module-level TTL cache (used in tests).
    """
    global _cached_cookie, _cached_at

    now = time.monotonic()
    if use_cache and _cached_cookie and (now - _cached_at) < _CACHE_TTL_SECONDS:
        return _cached_cookie

    cookie = _build_cookie_header(db_path or _CURSOR_DB_PATH)
    if use_cache:
        _cached_cookie = cookie
        _cached_at = now
    return cookie
