"""MCP tools: ledger_log, ledger_batch_log, ledger_search, ledger_context,
ledger_by_ref, ledger_open_threads, ledger_projects, ledger_register_project,
sync_ledger_from_files.

Follows the ``sync_tools.py`` shape: every tool opens a fresh connection via
a module-level, test-monkeypatchable ``_get_conn()`` and closes it before
returning. Mounted into the main ``sb`` FastMCP in ``mcp_app.py``.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from fastmcp import FastMCP

from .ledger_session import resolve_session_id
from .ledger_sync import append_to_changelog, sync_from_files
from .store import ledger as ledger_store

mcp = FastMCP(
    "sb-ledger",
    instructions=(
        "Append-only narrative ledger. ledger_log records one action; nothing "
        "here ever updates or deletes a past entry. Corrections are new rows "
        "with action_verb='Corrected'."
    ),
)


# ---------------------------------------------------------------------------
# Patchable helpers (override in tests via monkeypatch)
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def ledger_log(
    summary: str,
    project: str,
    action_verb: str = "Note",
    body: Optional[str] = None,
    scope: Optional[str] = None,
    refs: Optional[list[dict]] = None,
    session_id: Optional[str] = None,
    agent: Optional[str] = None,
    working_dir: Optional[str] = None,
    source_harness: str = "mcp",
) -> dict:
    """Record one narrative ledger entry. Append-only; never updates or deletes.

    Resolves (or reuses within a 30-minute window) a session id, redacts
    secrets deterministically, then inserts into ``sb_ledger``. When the
    project is enrolled in the registry with ``sync_mode='dual'``, the same
    entry is also appended to that project's ``CHANGELOG.md``.

    Args:
        summary: One-line narrative summary of the action taken.
        project: Project key, e.g. ``"sb"`` or ``"ciq"``.
        action_verb: Past-tense verb leading the bullet (default ``"Note"``).
        body: Optional longer narrative body.
        scope: Optional scope label rendered as the trailing ``*`scope`*``.
        refs: Optional list of ``{"kind", "value", "url"?, "label"?}`` dicts.
        session_id: Explicit session id to use instead of resolving one.
        agent: Harness/agent name (e.g. ``"cursor"``, ``"opencode"``).
        working_dir: Working directory the action was taken from.
        source_harness: Provenance tag for the entry (default ``"mcp"``).
    """
    conn = _get_conn()
    try:
        resolved_session = resolve_session_id(
            conn,
            agent=agent or "unknown",
            project=project,
            working_dir=working_dir,
            extras=None,
            explicit=session_id,
        )
        result = ledger_store.append_ledger(
            conn,
            project=project,
            summary=summary,
            action_verb=action_verb,
            body=body,
            scope=scope,
            refs=refs,
            session_id=resolved_session,
            agent=agent,
            working_dir=working_dir,
            source_harness=source_harness,
        )

        persisted_to_file = False
        if result["was_new"]:
            registry_row = conn.execute(
                "SELECT * FROM sb_project_registry WHERE project = ?", (project,)
            ).fetchone()
            if registry_row is not None and registry_row["sync_mode"] == "dual":
                full_row = ledger_store.get_ledger(conn, result["id"])
                if full_row is not None:
                    from pathlib import Path

                    append_to_changelog(
                        Path(registry_row["changelog_path"]).expanduser(), full_row
                    )
                    persisted_to_file = True

        result = dict(result)
        result["session_id"] = resolved_session
        result["persisted_to_file"] = persisted_to_file
        return result
    finally:
        conn.close()


@mcp.tool()
def ledger_batch_log(entries: list[dict]) -> dict:
    """Record multiple ledger entries in one call. Each dict accepts the
    same fields as ``ledger_log``. Returns ``{"results": [...]}`` in order;
    one entry's failure never blocks the others."""
    results: list[dict] = []
    for entry in entries:
        try:
            result = ledger_log(
                summary=entry["summary"],
                project=entry["project"],
                action_verb=entry.get("action_verb", "Note"),
                body=entry.get("body"),
                scope=entry.get("scope"),
                refs=entry.get("refs"),
                session_id=entry.get("session_id"),
                agent=entry.get("agent"),
                working_dir=entry.get("working_dir"),
                source_harness=entry.get("source_harness", "mcp"),
            )
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            results.append({"error": str(exc), "entry": entry})
    return {"results": results}


@mcp.tool()
def ledger_search(
    q: Optional[str] = None,
    project: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    verb: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Search the ledger. ``q`` performs a full-text match; structured
    filters (project/since/until/verb/session_id) combine as AND."""
    conn = _get_conn()
    try:
        return ledger_store.search_ledger(
            conn,
            q=q,
            project=project,
            since=since,
            until=until,
            verb=verb,
            session_id=session_id,
            limit=limit,
        )
    finally:
        conn.close()


@mcp.tool()
def ledger_context(project: str, since: Optional[str] = None, limit: int = 30) -> dict:
    """Return recent entries, open threads, and tracked refs for a project.
    Default window is the last 48 hours."""
    conn = _get_conn()
    try:
        return ledger_store.get_context(conn, project=project, since=since, limit=limit)
    finally:
        conn.close()


@mcp.tool()
def ledger_by_ref(kind: str, value: str, limit: int = 50) -> list[dict]:
    """Return ledger rows whose refs include a ``{kind, value}`` pair, e.g.
    ``kind="jira", value="CXP-45827"``."""
    conn = _get_conn()
    try:
        return ledger_store.by_ref(conn, kind=kind, value=value, limit=limit)
    finally:
        conn.close()


@mcp.tool()
def ledger_open_threads(project: Optional[str] = None) -> list[dict]:
    """Return ledger entries from the last 30 days whose refs point at a
    JIRA ticket still open in the local mirror or a todo still open in
    sb-todos."""
    conn = _get_conn()
    try:
        return ledger_store.open_threads(conn, project=project)
    finally:
        conn.close()


@mcp.tool()
def ledger_projects() -> list[dict]:
    """List all enrolled projects in the ledger registry."""
    conn = _get_conn()
    try:
        return ledger_store.list_projects(conn)
    finally:
        conn.close()


@mcp.tool()
def ledger_register_project(
    project: str,
    root_path: str,
    changelog_path: Optional[str] = None,
    sync_mode: str = "dual",
) -> dict:
    """Enroll (or update) a project in the ledger registry.

    ``changelog_path`` defaults to ``<root_path>/CHANGELOG.md`` when omitted.
    ``sync_mode`` is ``"dual"`` (SQLite + CHANGELOG.md) or ``"sqlite-only"``.
    """
    conn = _get_conn()
    try:
        return ledger_store.register_project(
            conn,
            project=project,
            root_path=root_path,
            changelog_path=changelog_path,
            sync_mode=sync_mode,
        )
    finally:
        conn.close()


@mcp.tool()
def sync_ledger_from_files() -> dict:
    """Hydrate the ledger from bullets already present in every enrolled
    project's CHANGELOG.md. Never writes to any file. Idempotent."""
    conn = _get_conn()
    try:
        projects = ledger_store.list_projects(conn)
        return sync_from_files(conn, projects)
    finally:
        conn.close()
