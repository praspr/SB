"""DB-backed goals registry MCP tools: CRUD, alignment scoring, and a
last-7-days heatmap.

Separate from the existing YAML-fed ``goals.py`` (``get_goals`` in
``ritual_tools.py``) by design — this is the SQLite-backed registry that the
web UI's goals/tiers page will read and write. Tool names use a ``_v2``
suffix to avoid colliding with the existing ``get_goals`` tool.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastmcp import FastMCP

mcp = FastMCP(
    "sb-goals",
    instructions=(
        "DB-backed goals registry (contractual/quarterly/weekly tiers). "
        "archive_goal is a status transition, never a delete."
    ),
)

_VALID_TIERS = {"contractual", "quarterly", "weekly"}
_VALID_STATUSES = {"active", "done", "archived"}


def _get_conn() -> sqlite3.Connection:
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_goal(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["keywords"] = json.loads(d.get("keywords") or "[]")
    except json.JSONDecodeError:
        d["keywords"] = []
    return d


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9-]+", (text or "").lower()) if len(w) > 1}


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@mcp.tool()
def list_goals_v2(tier: Optional[str] = None, status: Optional[str] = "active") -> list[dict]:
    """List goals from the DB-backed registry, optionally filtered by tier
    (contractual/quarterly/weekly) and status (active/done/archived).
    Pass ``status=None`` to include every status."""
    conn = _get_conn()
    try:
        clauses: list[str] = []
        params: list[object] = []
        if tier:
            clauses.append("tier = ?")
            params.append(tier)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM sb_goals_registry {where} ORDER BY tier, id", params
        ).fetchall()
        return [_row_to_goal(row) for row in rows]
    finally:
        conn.close()


@mcp.tool()
def get_goal_v2(id: int) -> Optional[dict]:
    """Return one goal by id, or None if it does not exist."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sb_goals_registry WHERE id = ?", (id,)
        ).fetchone()
        return _row_to_goal(row) if row is not None else None
    finally:
        conn.close()


@mcp.tool()
def add_goal(
    tier: str,
    title: str,
    description: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    target_date: Optional[str] = None,
) -> dict:
    """Add a goal to the registry. ``tier`` is contractual, quarterly, or
    weekly. ``keywords`` drive alignment scoring against todos/ledger rows."""
    if tier not in _VALID_TIERS:
        raise ValueError(f"tier must be one of {sorted(_VALID_TIERS)}")
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO sb_goals_registry (tier, title, description, keywords, target_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (tier, title, description, json.dumps(keywords or []), target_date),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sb_goals_registry WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_goal(row)
    finally:
        conn.close()


@mcp.tool()
def update_goal(
    id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    target_date: Optional[str] = None,
    tier: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """Update the provided fields of a goal. Only supplied fields change."""
    if tier is not None and tier not in _VALID_TIERS:
        raise ValueError(f"tier must be one of {sorted(_VALID_TIERS)}")
    if status is not None and status not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {sorted(_VALID_STATUSES)}")

    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT * FROM sb_goals_registry WHERE id = ?", (id,)
        ).fetchone()
        if existing is None:
            raise ValueError(f"goal {id} not found")

        fields: dict[str, object] = {}
        if title is not None:
            fields["title"] = title
        if description is not None:
            fields["description"] = description
        if keywords is not None:
            fields["keywords"] = json.dumps(keywords)
        if target_date is not None:
            fields["target_date"] = target_date
        if tier is not None:
            fields["tier"] = tier
        if status is not None:
            fields["status"] = status

        if fields:
            fields["updated_at"] = _now_utc()
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(
                f"UPDATE sb_goals_registry SET {set_clause} WHERE id = ?",
                (*fields.values(), id),
            )
            conn.commit()

        row = conn.execute(
            "SELECT * FROM sb_goals_registry WHERE id = ?", (id,)
        ).fetchone()
        return _row_to_goal(row)
    finally:
        conn.close()


@mcp.tool()
def archive_goal(id: int) -> dict:
    """Archive a goal (status transition to 'archived'). Never deletes a row."""
    return update_goal(id, status="archived")


# ---------------------------------------------------------------------------
# Alignment scoring
# ---------------------------------------------------------------------------


def _score_text(text: str, goal_keywords: set[str]) -> float:
    if not goal_keywords:
        return 0.0
    text_words = _words(text)
    hits = sum(1 for kw in goal_keywords if kw in text_words)
    return round(hits / len(goal_keywords), 4)


@mcp.tool()
def score_alignment(
    todo_id: Optional[int] = None, ledger_id: Optional[int] = None
) -> list[dict]:
    """Score one todo or one ledger row against every active goal's keywords.

    Returns ``[{"goal_id": int, "score": float}, ...]`` for active goals,
    sorted by score descending. Score is keyword-overlap count normalized by
    the goal's keyword count (0..1). No LLM is used.
    """
    if (todo_id is None) == (ledger_id is None):
        raise ValueError("exactly one of todo_id or ledger_id must be provided")

    conn = _get_conn()
    try:
        goals = conn.execute(
            "SELECT * FROM sb_goals_registry WHERE status = 'active'"
        ).fetchall()

        if todo_id is not None:
            text = _todo_text(todo_id)
        else:
            text = _ledger_text(conn, ledger_id)

        results: list[dict] = []
        for goal_row in goals:
            goal = _row_to_goal(goal_row)
            keywords = {k.lower() for k in goal["keywords"]}
            score = _score_text(text, keywords)
            results.append({"goal_id": goal["id"], "score": score})
        return sorted(results, key=lambda r: r["score"], reverse=True)
    finally:
        conn.close()


def _todo_text(todo_id: int) -> str:
    try:
        from sb_todos import handlers as todo_handlers
        from sb_todos.config import settings as todo_settings
        from sb_todos.db import connect as connect_todos
    except Exception:  # noqa: BLE001
        return ""
    todos_conn = None
    try:
        todos_conn = connect_todos(todo_settings.db_path)
        todo = todo_handlers.get_todo(todos_conn, todo_id)
        if todo is None:
            return ""
        return f"{todo.title} {todo.description or ''}"
    except Exception:  # noqa: BLE001
        return ""
    finally:
        if todos_conn is not None:
            todos_conn.close()


def _ledger_text(conn: sqlite3.Connection, ledger_id: int) -> str:
    from .store.ledger import get_ledger

    row = get_ledger(conn, ledger_id)
    if row is None:
        return ""
    return f"{row.get('summary', '')} {row.get('body') or ''}"


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------


@mcp.tool()
def heatmap_last_week() -> list[dict]:
    """For each active goal, count matching ledger entries and completed
    todos in the last 7 days, plus the top referenced values.

    Returns ``[{"goal_id", "ledger_count", "todo_count", "top_refs"}, ...]``.
    A ledger entry or completed todo "matches" a goal when at least one of
    the goal's keywords appears in its text (title/summary + body).
    """
    conn = _get_conn()
    try:
        goals = [
            _row_to_goal(row)
            for row in conn.execute(
                "SELECT * FROM sb_goals_registry WHERE status = 'active'"
            ).fetchall()
        ]
        if not goals:
            return []

        since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        from .store.ledger import search_ledger

        recent_entries = search_ledger(conn, since=since, limit=1000)

        completed_todos = _completed_todos_since(since)

        results: list[dict] = []
        for goal in goals:
            keywords = {k.lower() for k in goal["keywords"]}
            ref_counter: Counter[str] = Counter()

            ledger_count = 0
            for entry in recent_entries:
                text = f"{entry.get('summary', '')} {entry.get('body') or ''}"
                if keywords and _words(text) & keywords:
                    ledger_count += 1
                    for ref in entry.get("refs") or []:
                        if isinstance(ref, dict) and ref.get("value"):
                            ref_counter[str(ref["value"])] += 1

            todo_count = 0
            for todo_text in completed_todos:
                if keywords and _words(todo_text) & keywords:
                    todo_count += 1

            results.append(
                {
                    "goal_id": goal["id"],
                    "ledger_count": ledger_count,
                    "todo_count": todo_count,
                    "top_refs": [ref for ref, _ in ref_counter.most_common(5)],
                }
            )
        return results
    finally:
        conn.close()


def _completed_todos_since(since: str) -> list[str]:
    try:
        from sb_todos import handlers as todo_handlers
        from sb_todos.config import settings as todo_settings
        from sb_todos.db import connect as connect_todos
    except Exception:  # noqa: BLE001
        return []
    todos_conn = None
    try:
        todos_conn = connect_todos(todo_settings.db_path)
        todos = todo_handlers.list_todos(todos_conn, status="completed", limit=1000)
    except Exception:  # noqa: BLE001
        return []
    finally:
        if todos_conn is not None:
            todos_conn.close()

    texts: list[str] = []
    for todo in todos:
        completed_at = getattr(todo, "completed_at", None) or ""
        if completed_at and completed_at < since:
            continue
        texts.append(f"{todo.title} {todo.description or ''}")
    return texts
