"""claudegate LLM client with a SHA-256 content cache.

- Base URL / timeout / model come from settings (no credentials anywhere).
- Responses are cached by ``sha256(model + "\\n" + prompt)`` under the cache
  directory.  The SHA-256 here is a *content addressing* hash, not a security
  primitive.
- Uses ``httpx`` with a bounded timeout.  Prompt content is never logged.
- If the backend is unreachable/errors, ``LLMUnavailable`` is raised so callers
  can fall back deterministically.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_MAX_TOKENS = 1024
# Upper bound on cached/returned response length (defensive: avoid unbounded
# memory / disk from a misbehaving backend).
_MAX_RESPONSE_CHARS = 200_000


class LLMUnavailable(RuntimeError):
    """Raised when the LLM backend cannot satisfy a request."""


# ---------------------------------------------------------------------------
# Settings accessors (patchable in tests)
# ---------------------------------------------------------------------------


def _base_url() -> str:
    from .config import settings

    return settings.llm_base_url


def _timeout() -> float:
    from .config import settings

    return float(settings.llm_timeout)


def _model() -> str:
    from .config import settings

    return settings.llm_model


def _tier() -> str | None:
    from .config import settings

    return settings.llm_tier


def _cache_dir() -> Path:
    from .config import settings

    return Path(settings.llm_cache_dir).expanduser()


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def cache_key(
    model: str,
    prompt: str,
    *,
    tier: str | None = None,
    max_tokens: int = _MAX_TOKENS,
) -> str:
    """Content-addressing key (SHA-256, not a security primitive).

    Includes the request parameters that change the response — model, tier, and
    ``max_tokens`` — so different request shapes never collide in the cache.
    """
    material = f"{model}\n{tier}\n{max_tokens}\n{prompt}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _cache_file(model: str, prompt: str, *, tier: str | None, max_tokens: int) -> Path:
    key = cache_key(model, prompt, tier=tier, max_tokens=max_tokens)
    return _cache_dir() / f"{key}.txt"


def _read_cache(path: Path) -> str | None:
    """Return cached text, or None on any read/decode error or empty content."""
    try:
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        # Corrupt or unreadable cache entry -> treat as a miss.
        return None
    if not text:
        return None
    return text


def _write_cache(path: Path, text: str) -> None:
    """Atomically write *text* via a temp file + os.replace (no partial files)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        logger.warning("failed to write LLM cache entry")
        try:
            if tmp.exists():  # type: ignore[possibly-undefined]
                tmp.unlink()
        except (OSError, NameError):
            pass


# ---------------------------------------------------------------------------
# HTTP (patchable in tests)
# ---------------------------------------------------------------------------


def _http_post(url: str, payload: dict, timeout: float) -> dict:
    """POST ``payload`` to *url* and return the decoded JSON body."""
    response = httpx.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _extract_text(data: Any) -> str:
    """Extract assistant text from a claudegate/OpenAI-style response body."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = (
                choices[0].get("message") if isinstance(choices[0], dict) else None
            )
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(choices[0], dict) and isinstance(choices[0].get("text"), str):
                return choices[0]["text"]
        if isinstance(data.get("content"), str):
            return data["content"]
    raise LLMUnavailable("unrecognized LLM response shape")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def complete(prompt: str, *, model: str | None = None) -> str:
    """Return a completion for *prompt*, using the cache when available.

    Raises ``LLMUnavailable`` on any backend/transport error.
    """
    model_name = model or _model()
    tier = _tier()
    cache_file = _cache_file(model_name, prompt, tier=tier, max_tokens=_MAX_TOKENS)

    cached = _read_cache(cache_file)
    if cached is not None:
        return cached

    payload = {
        "model": model_name,
        "max_tokens": _MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    if tier:
        payload["tier"] = tier
    url = _base_url().rstrip("/") + "/v1/chat/completions"

    try:
        data = _http_post(url, payload, _timeout())
    except LLMUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - transport/JSON/etc.
        # Never include prompt content in the log.
        logger.warning("LLM backend unavailable: %s", type(exc).__name__)
        raise LLMUnavailable(str(type(exc).__name__)) from exc

    text = _extract_text(data)[:_MAX_RESPONSE_CHARS]
    _write_cache(cache_file, text)
    return text
