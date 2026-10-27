"""Append-only narrative ledger storage: insert, search, and project registry.

Design:
- ``append_ledger`` is idempotent by ``content_sha256`` — a duplicate call
  (same project+summary+body) returns the existing row instead of raising.
- No UPDATE/DELETE ever touches ``sb_ledger`` (enforced by DB triggers, see
  ``store/db.py`` migration ``_m8_ledger``). Corrections are new rows with
  ``action_verb='Corrected'``.
- Every public function takes a ``sqlite3.Connection`` and never manages its
  own connection lifecycle; callers open/close per the repo's fresh-
  connection-per-call convention.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _content_sha256(project: str, summary: str, body: Optional[str]) -> str:
    material = f"{project}\u0001{summary}\u0001{body or ''}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["refs"] = json.loads(d.get("refs") or "[]")
    d["redaction_applied"] = bool(d.get("redaction_applied"))
    return d


_FTS_OPERATOR_RE = re.compile(r'\b(?:AND|OR|NOT|NEAR)\b|[()^+\-:*]')


def _sanitize_fts_query(q: str) -> str:
    cleaned = _FTS_OPERATOR_RE.sub(" ", q)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().replace('"', '')
    if not cleaned:
        return ''
    return f'"{cleaned}"'


# ---------------------------------------------------------------------------
# Append / lookup
# ---------------------------------------------------------------------------


def append_ledger(
    conn: sqlite3.Connection,
    *,
    project: str,
    summary: str,
    action_verb: str = "Note",
    body: Optional[str] = None,
    scope: Optional[str] = None,
    refs: Optional[list[dict]] = None,
    session_id: Optional[str] = None,
    agent: Optional[str] = None,
    working_dir: Optional[str] = None,
    source_harness: str = "mcp",
    agent_model: Optional[str] = None,
    origin: str = "ledger_log",
    ts: Optional[str] = None,
) -> dict:
    """Redact, hash, and insert one ledger row. Idempotent by content hash.

    Never raises for content reasons. ``session_id`` must already be
    resolved by the caller (see ``ledger_session.resolve_session_id``); this
    function does not derive one on its own so it stays a pure storage
    primitive.

    Returns ``{"id", "ts", "redaction_applied", "was_new"}``.
    """
    from ..ledger_redact import redact_entry

    scrubbed_summary, scrubbed_body, scrubbed_refs, redaction_applied = redact_entry(
        summary=summary, body=body, refs=refs
    )

    content_sha256 = _content_sha256(project, scrubbed_summary, scrubbed_body)

    existing = conn.execute(
        "SELECT id, ts, redaction_applied FROM sb_ledger WHERE content_sha256 = ?",
        (content_sha256,),
    ).fetchone()
    if existing is not None:
        return {
            "id": existing["id"],
            "ts": existing["ts"],
            "redaction_applied": bool(existing["redaction_applied"]),
            "was_new": False,
        }

    from ..ledger_redact import REDACTION_RULES_VERSION

    row_ts = ts or _now_utc()
    conn.execute(
        """
        INSERT INTO sb_ledger (
          ts, session_id, project, scope, action_verb, summary, body, refs,
          source_harness, agent_model, working_dir, origin,
          redaction_applied, redaction_rules_version, content_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_ts,
            session_id or "",
            project,
            scope,
            action_verb,
            scrubbed_summary,
            scrubbed_body,
            json.dumps(scrubbed_refs or []),
            source_harness,
            agent_model,
            working_dir,
            origin,
            1 if redaction_applied else 0,
            REDACTION_RULES_VERSION,
            content_sha256,
        ),
    )
    new_id = conn.execute(
        "SELECT id FROM sb_ledger WHERE content_sha256 = ?", (content_sha256,)
    ).fetchone()["id"]

    # Populate the normalized refs index (M2). Derived child rows; the ledger
    # itself stays append-only.
    _index_refs(conn, new_id, scrubbed_refs or [])

    conn.commit()

    return {
        "id": new_id,
        "ts": row_ts,
        "redaction_applied": redaction_applied,
        "was_new": True,
    }


def _index_refs(conn: sqlite3.Connection, ledger_id: int, refs: list[dict]) -> None:
    """Insert ``{ledger_id, kind, value}`` rows into ``sb_ledger_refs``.

    Best-effort and tolerant of an older schema (pre-m12): if the table does
    not exist yet, silently skip indexing.
    """
    try:
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            kind = ref.get("kind")
            value = ref.get("value")
            if isinstance(kind, str) and value is not None:
                conn.execute(
                    "INSERT INTO sb_ledger_refs (ledger_id, kind, value) VALUES (?, ?, ?)",
                    (ledger_id, kind, str(value)),
                )
    except sqlite3.OperationalError:
        # sb_ledger_refs not present (schema older than m12) — skip.
        pass


def get_ledger(conn: sqlite3.Connection, ledger_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM sb_ledger WHERE id = ?", (ledger_id,)).fetchone()
    return _row_to_dict(row) if row is not None else None


def search_ledger(
    conn: sqlite3.Connection,
    *,
    q: Optional[str] = None,
    project: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    verb: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Search the ledger. Uses FTS when ``q`` is given; structured filters
    (project/since/until/verb/session_id) always combine as AND."""
    clauses: list[str] = []
    params: list[object] = []

    if project:
        clauses.append("l.project = ?")
        params.append(project)
    if since:
        clauses.append("l.ts >= ?")
        params.append(since)
    if until:
        clauses.append("l.ts < ?")
        params.append(until)
    if verb:
        clauses.append("l.action_verb = ?")
        params.append(verb)
    if session_id:
        clauses.append("l.session_id = ?")
        params.append(session_id)

    where = f"AND {' AND '.join(clauses)}" if clauses else ""

    if q:
        fts_query = _sanitize_fts_query(q)
        if not fts_query:
            return []
        sql = f"""
            SELECT l.* FROM sb_ledger_fts f
            JOIN sb_ledger l ON l.id = f.rowid
            WHERE sb_ledger_fts MATCH ? {where}
            ORDER BY l.ts DESC
            LIMIT ?
        """
        params_full = [fts_query, *params, limit]
    else:
        where_all = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT l.* FROM sb_ledger l
            {where_all}
            ORDER BY l.ts DESC
            LIMIT ?
        """
        params_full = [*params, limit]

    rows = conn.execute(sql, params_full).fetchall()
    return [_row_to_dict(row) for row in rows]


def by_ref(conn: sqlite3.Connection, *, kind: str, value: str, limit: int = 50) -> list[dict]:
    """Return ledger rows whose ``refs`` include a ``{kind, value}`` pair.

    Uses the normalized ``sb_ledger_refs`` index (M2). Falls back to a bounded
    full scan + Python filter when the index is absent (schema older than m12).
    """
    try:
        rows = conn.execute(
            """
            SELECT l.* FROM sb_ledger_refs r
            JOIN sb_ledger l ON l.id = r.ledger_id
            WHERE r.kind = ? AND r.value = ?
            ORDER BY l.ts DESC
            LIMIT ?
            """,
            (kind, str(value), limit),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    except sqlite3.OperationalError:
        return _by_ref_scan(conn, kind=kind, value=value, limit=limit)


def _by_ref_scan(conn: sqlite3.Connection, *, kind: str, value: str, limit: int = 50) -> list[dict]:
    """Legacy fallback: bounded full scan + Python JSON filter (pre-m12)."""
    rows = conn.execute(
        "SELECT * FROM sb_ledger ORDER BY ts DESC LIMIT 2000"
    ).fetchall()
    matched: list[dict] = []
    for row in rows:
        d = _row_to_dict(row)
        for ref in d["refs"]:
            if not isinstance(ref, dict):
                continue
            if ref.get("kind") == kind and ref.get("value") == value:
                matched.append(d)
                break
        if len(matched) >= limit:
            break
    return matched


def open_threads(conn: sqlite3.Connection, *, project: Optional[str] = None) -> list[dict]:
    """Heuristic: ledger entries from the last 30 days whose refs include a
    JIRA key still open in the local JIRA mirror, or a todo id still open in
    sb-todos. Returns ledger rows enriched with an ``open_status`` field.

    Cross-service lookups are best-effort: if sb_jira or sb_todos cannot be
    reached (not installed, no local data), that ref kind is simply skipped
    rather than raising.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    clauses = ["ts >= ?"]
    params: list[object] = [since]
    if project:
        clauses.append("project = ?")
        params.append(project)
    where = f"WHERE {' AND '.join(clauses)}"
    rows = conn.execute(
        f"SELECT * FROM sb_ledger {where} ORDER BY ts DESC LIMIT 500", params
    ).fetchall()
    entries = [_row_to_dict(row) for row in rows]

    open_jira_keys = _open_jira_keys()
    open_todo_ids = _open_todo_ids()

    result: list[dict] = []
    for entry in entries:
        open_refs: list[dict] = []
        for ref in entry["refs"]:
            if not isinstance(ref, dict):
                continue
            kind = ref.get("kind")
            value = ref.get("value")
            if kind == "jira" and value in open_jira_keys:
                open_refs.append({**ref, "open": True})
            elif kind == "todo" and _coerce_int(value) in open_todo_ids:
                open_refs.append({**ref, "open": True})
        if open_refs:
            entry_with_status = dict(entry)
            entry_with_status["open_status"] = "open"
            entry_with_status["open_refs"] = open_refs
            result.append(entry_with_status)
    return result


def _coerce_int(value: object) -> Optional[int]:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _open_jira_keys() -> set[str]:
    """Best-effort: keys of tickets not in a closed-like status in the local
    JIRA markdown mirror. Returns an empty set if sb_jira is unavailable."""
    try:
        from sb_jira import file_store as jira_file_store
    except Exception:  # noqa: BLE001
        return set()
    try:
        tickets = jira_file_store.load_all()
    except Exception:  # noqa: BLE001
        return set()
    closed = {"closed", "done", "resolved", "cancelled"}
    open_keys: set[str] = set()
    for detail in tickets:
        ticket = jira_file_store.to_ticket(detail)
        status = (ticket.status or "").strip().lower()
        if status not in closed:
            open_keys.add(ticket.key)
    return open_keys


def _open_todo_ids() -> set[int]:
    """Best-effort: ids of open todos in sb-todos. Empty set if unavailable."""
    try:
        from sb_todos import handlers as todo_handlers
        from sb_todos.config import settings as todo_settings
        from sb_todos.db import connect as connect_todos
    except Exception:  # noqa: BLE001
        return set()
    try:
        todos_conn = connect_todos(todo_settings.db_path)
    except Exception:  # noqa: BLE001
        return set()
    try:
        todos = todo_handlers.list_todos(todos_conn, status="open", limit=1000)
        return {t.id for t in todos}
    except Exception:  # noqa: BLE001
        return set()
    finally:
        todos_conn.close()


def get_context(
    conn: sqlite3.Connection,
    *,
    project: str,
    since: Optional[str] = None,
    limit: int = 30,
) -> dict:
    """Return recent ledger entries, open threads, and tracked refs for a
    project. Default window is the last 48 hours."""
    since_value = since or (
        datetime.now(timezone.utc) - timedelta(hours=48)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    entries = search_ledger(conn, project=project, since=since_value, limit=limit)
    threads = open_threads(conn, project=project)

    tracked_refs: dict[tuple[str, str], dict] = {}
    for entry in entries:
        for ref in entry["refs"]:
            if not isinstance(ref, dict):
                continue
            kind = ref.get("kind")
            value = ref.get("value")
            if not isinstance(kind, str) or not isinstance(value, str):
                continue
            key = (kind, value)
            if key not in tracked_refs:
                tracked_refs[key] = ref

    return {
        "entries": entries,
        "open_threads": threads,
        "tracked_refs": list(tracked_refs.values()),
    }


# ---------------------------------------------------------------------------
# Project registry
# ---------------------------------------------------------------------------


def list_projects(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM sb_project_registry ORDER BY project"
    ).fetchall()
    return [dict(row) for row in rows]


def register_project(
    conn: sqlite3.Connection,
    *,
    project: str,
    root_path: str,
    changelog_path: Optional[str] = None,
    sync_mode: str = "dual",
) -> dict:
    """Insert or update a project registry row (idempotent by project name)."""
    from pathlib import Path

    resolved_changelog = changelog_path or str(Path(root_path).expanduser() / "CHANGELOG.md")
    conn.execute(
        """
        INSERT INTO sb_project_registry (project, root_path, changelog_path, sync_mode)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(project) DO UPDATE SET
          root_path = excluded.root_path,
          changelog_path = excluded.changelog_path,
          sync_mode = excluded.sync_mode
        """,
        (project, root_path, resolved_changelog, sync_mode),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM sb_project_registry WHERE project = ?", (project,)
    ).fetchone()
    return dict(row)
