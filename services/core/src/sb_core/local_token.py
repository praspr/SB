"""Local shared-secret token for gating write-capable MCP tools (M5).

A single-user localhost service still shouldn't let any local process (or a
malicious page hitting 127.0.0.1) silently drive write tools. This module
issues a per-install token stored at ``~/.local/share/sb/local_token`` with
mode ``0o600`` and provides a constant-time check.

The token is never logged. Read tools are unaffected — only the write-capable
subset is gated (see ``local_gate.py``).
"""

from __future__ import annotations

import hmac
import logging
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

_TOKEN_PATH = Path("~/.local/share/sb/local_token").expanduser()

_cached_token: str | None = None


def _read_token_file(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        value = path.read_text(encoding="utf-8").strip()
        return value or None
    except OSError:
        return None


def ensure_token(path: Path | None = None) -> str:
    """Return the local token, generating and persisting one (0o600) if absent."""
    global _cached_token
    target = path or _TOKEN_PATH
    if _cached_token and path is None:
        return _cached_token

    existing = _read_token_file(target)
    if existing:
        if path is None:
            _cached_token = existing
        return existing

    token = secrets.token_urlsafe(32)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(token, encoding="utf-8")
        target.chmod(0o600)
    except OSError:
        # Fail soft: if we cannot persist, still return a token for this
        # process so the service keeps working; it just won't survive a restart.
        logger.warning("could not persist local token file")
    if path is None:
        _cached_token = token
    return token


def token_matches(candidate: str | None, path: Path | None = None) -> bool:
    """Constant-time comparison of *candidate* against the stored local token."""
    if not candidate:
        return False
    expected = ensure_token(path)
    return hmac.compare_digest(candidate, expected)


def reset_cache() -> None:
    """Testing hook: clear the in-process token cache."""
    global _cached_token
    _cached_token = None
