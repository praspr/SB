"""Local list of JIRA keys that stay in the mirror beyond the assigned JQL."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from .config import settings

_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
_BROWSE_RE = re.compile(r"^/browse/([A-Za-z][A-Za-z0-9]*-\d+)$")


def parse_issue(raw: str, site: str) -> str:
    """Normalize a key or configured browse URL. Reject every other input."""
    text = raw.strip()
    if not text:
        raise ValueError("Enter a JIRA key or link")
    if "://" in text:
        parsed = urlparse(text)
        expected = urlparse(site)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname != expected.hostname
        ):
            raise ValueError(
                "Only links from the configured Atlassian site are accepted"
            )
        match = _BROWSE_RE.fullmatch(parsed.path)
        if not match:
            raise ValueError("That link is not a JIRA issue")
        return match.group(1).upper()
    key = text.upper()
    if not _KEY_RE.fullmatch(key):
        raise ValueError("Enter a JIRA key such as CXP-123 or a browse link")
    return key


def load_keys(path: Path | None = None) -> list[str]:
    target = path or settings.tracked_path
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    keys = payload.get("keys") if isinstance(payload, dict) else None
    if not isinstance(keys, list):
        return []
    return sorted(
        {str(key).upper() for key in keys if _KEY_RE.fullmatch(str(key).upper())}
    )


def save_keys(keys: list[str], path: Path | None = None) -> None:
    target = path or settings.tracked_path
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            {"version": 1, "keys": sorted(set(keys))},
            indent=2,
        )
        + "\n"
    )
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, target)


def add_key(key: str, path: Path | None = None) -> None:
    save_keys([*load_keys(path), key.upper()], path)


def remove_key(key: str, path: Path | None = None) -> None:
    save_keys([item for item in load_keys(path) if item != key.upper()], path)
