"""MCP tools: sync_adapters, sync_status, search_signals.

Mounted into the main sb FastMCP in mcp_app.py.

Connection policy: every tool call opens a **fresh** connection via
``_get_conn()`` and closes it before returning.  No process-wide singleton.
``_get_conn`` is a module-level function so tests can monkeypatch it.

Adapter execution in ``sync_adapters`` uses ``_run_one_adapter`` which calls
the subprocess-based ``run_adapter_by_name``.  Tests monkeypatch
``_run_one_adapter`` to avoid spawning real processes.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from .adapters import AdapterResult, get_sync_states, run_adapter_by_name
from .store import signals as _signal_store
from .store.db import connect

logger = logging.getLogger(__name__)

mcp = FastMCP("sb-sync")

_ALL_ADAPTERS: tuple[str, ...] = ("todos", "jira", "changelog", "git")


# ---------------------------------------------------------------------------
# Patchable helpers (override in tests via monkeypatch)
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    """Open a fresh connection for this operation (no singleton).

    Tests patch this to ``lambda: connect(tmp_path / 'core.db')`` so each
    tool call gets a fresh file-backed connection to the test DB.
    """
    from .config import settings

    return connect(settings.db_path)


def _get_roots() -> list[Path]:
    from .config import settings

    return [Path(r) for r in settings.roots]


def _get_git_authors() -> Optional[list[str]]:
    from .config import settings

    return settings.git_authors or None


def _run_one_adapter(name: str, db_path: Path | str, config: dict) -> AdapterResult:
    """Production: subprocess per adapter, truly bounded timeout.

    Tests monkeypatch this to return a mock ``AdapterResult`` without spawning.
    """
    return run_adapter_by_name(name, db_path, config, timeout=30.0)


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
def sync_adapters(
    adapters: list[str] | None = None,
    since_days: int = 30,
) -> dict:
    """Run signal sync adapters and return per-adapter counts and errors.

    Never fails the whole sync due to a single adapter error.

    Args:
        adapters: Subset of adapter names to run, or ``None`` for all
            (todos, jira, changelog, git).
        since_days: Look-back window in days for the git adapter.

    Returns:
        ``{"adapters": {<name>: {"signal_count": int, "error": str | None}}}``
    """
    from .config import settings

    names = list(adapters) if adapters is not None else list(_ALL_ADAPTERS)
    db_path = settings.db_path
    roots = _get_roots()
    git_authors = _get_git_authors()
    config = {
        "roots": [str(r) for r in roots],
        "since_days": since_days,
        "git_authors": git_authors or [],
    }

    results: dict[str, dict] = {}
    for name in names:
        if name not in _ALL_ADAPTERS:
            results[name] = {
                "signal_count": 0,
                "error": f"unknown adapter: {name!r}",
            }
            continue
        result = _run_one_adapter(name, db_path, config)
        results[name] = {
            "signal_count": result.signal_count,
            "error": result.error,
        }

    return {"adapters": results}


@mcp.tool()
def sync_status() -> dict:
    """Return the last sync state for every adapter that has run.

    Returns:
        ``{"states": [{"adapter": str, "last_run_at": str, "signal_count": int,
        "error": str | None}]}``
    """
    conn = _get_conn()
    try:
        return {"states": get_sync_states(conn)}
    finally:
        conn.close()


@mcp.tool()
def search_signals(
    q: str | None = None,
    source: str | None = None,
    kind: str | None = None,
    since: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Search indexed local signals.  Results are citation-ready (include ``id``).

    Args:
        q: Substring match against ``title`` and ``body``.
        source: Filter by source name (``todos``, ``jira``, ``changelog``, ``git``).
        kind: Filter by kind (``task``, ``ticket``, ``release``, ``commit``).
        since: ISO UTC lower-bound for ``occurred_at``, e.g. ``"2026-01-01T00:00:00Z"``.
        limit: Maximum results to return (default 100).

    Returns:
        List of signal dicts.  Cite as ``[signal:<id>]``.
    """
    conn = _get_conn()
    try:
        signals = _signal_store.search_signals(
            conn, q=q, source=source, kind=kind, since=since, limit=limit
        )
        return [asdict(s) for s in signals]
    finally:
        conn.close()
