"""Pure handler functions shared by MCP tools and REST routes.

Every handler takes a sqlite3.Connection as first argument, plus keyword
arguments describing the operation. Handlers return Pydantic models (or
lists/bools) and never touch transport concerns (HTTP, MCP protocol, etc).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone

from .models import Todo, TodoCreate, TodoUpdate

_WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _row_to_todo(row: sqlite3.Row) -> Todo:
    data = dict(row)
    tags_raw = data.pop("tags", None)
    tags = json.loads(tags_raw) if tags_raw else []
    return Todo(
        id=data["id"],
        title=data["title"],
        description=data.get("description") or "",
        priority=data["priority"],
        due_date=data.get("due_date"),
        due_time=data.get("due_time"),
        is_completed=bool(data.get("is_completed")),
        completed_at=data.get("completed_at"),
        tags=tags,
        external_source=data.get("external_source"),
        external_ref=data.get("external_ref"),
        domain=data.get("domain", "work"),
        goal_id=data.get("goal_id"),
        jira_ref=data.get("jira_ref"),
        recurrence_rule=data.get("recurrence_rule"),
        parent_todo_id=data.get("parent_todo_id"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def list_todos(
    conn: sqlite3.Connection,
    *,
    status: str = "open",
    priority: int | None = None,
    domain: str | None = None,
    tag: str | None = None,
    limit: int = 100,
) -> list[Todo]:
    """List todos with optional filters. status: open|completed|all"""
    clauses: list[str] = []
    params: list[object] = []

    if status == "open":
        clauses.append("is_completed = 0")
    elif status == "completed":
        clauses.append("is_completed = 1")
    elif status == "all":
        pass
    else:
        raise ValueError(f"invalid status: {status!r} (must be open|completed|all)")

    if priority is not None:
        clauses.append("priority = ?")
        params.append(priority)

    if domain is not None:
        clauses.append("domain = ?")
        params.append(domain)

    if tag is not None:
        clauses.append("tags LIKE ?")
        params.append(f'%"{tag}"%')

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT * FROM todos
        {where}
        ORDER BY
          is_completed ASC,
          priority ASC,
          COALESCE(due_date, '9999-99-99') ASC,
          id DESC
        LIMIT ?
    """
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [_row_to_todo(row) for row in rows]


def get_todo(conn: sqlite3.Connection, todo_id: int) -> Todo | None:
    """Fetch a single todo by id, or None if not found."""
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return _row_to_todo(row) if row else None


def add_todo(conn: sqlite3.Connection, data: TodoCreate) -> Todo:
    """Create a new todo. If external_source/external_ref are provided and
    already exist, update that row instead (idempotent upsert)."""
    now = _now()
    tags_json = json.dumps(data.tags or [])

    if data.external_source and data.external_ref:
        existing = conn.execute(
            "SELECT id FROM todos WHERE external_source = ? AND external_ref = ?",
            (data.external_source, data.external_ref),
        ).fetchone()
        if existing:
            todo_id = existing["id"]
            conn.execute(
                """
                UPDATE todos SET
                  title = ?, description = ?, priority = ?, due_date = ?,
                  due_time = ?, tags = ?, domain = ?, goal_id = ?, jira_ref = ?,
                  recurrence_rule = ?, parent_todo_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    data.title,
                    data.description or "",
                    data.priority,
                    data.due_date,
                    data.due_time,
                    tags_json,
                    data.domain,
                    data.goal_id,
                    data.jira_ref,
                    data.recurrence_rule,
                    data.parent_todo_id,
                    now,
                    todo_id,
                ),
            )
            conn.commit()
            return get_todo(conn, todo_id)  # type: ignore[return-value]

    cursor = conn.execute(
        """
        INSERT INTO todos (
          title, description, priority, due_date, due_time, tags,
          external_source, external_ref, domain, goal_id, jira_ref,
          recurrence_rule, parent_todo_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.title,
            data.description or "",
            data.priority,
            data.due_date,
            data.due_time,
            tags_json,
            data.external_source,
            data.external_ref,
            data.domain,
            data.goal_id,
            data.jira_ref,
            data.recurrence_rule,
            data.parent_todo_id,
            now,
            now,
        ),
    )
    conn.commit()
    todo_id = cursor.lastrowid
    return get_todo(conn, todo_id)  # type: ignore[return-value]


def complete_todo(conn: sqlite3.Connection, todo_id: int) -> Todo:
    """Mark a todo as completed, setting completed_at and updated_at to now.

    If the todo has a ``recurrence_rule``, immediately materializes the next
    instance (idempotent -- see ``expand_recurring_todo``).
    """
    now = _now()
    existing = get_todo(conn, todo_id)
    if existing is None:
        raise ValueError(f"todo {todo_id} not found")
    conn.execute(
        "UPDATE todos SET is_completed = 1, completed_at = ?, updated_at = ? WHERE id = ?",
        (now, now, todo_id),
    )
    conn.commit()
    if existing.recurrence_rule:
        expand_recurring_todo(conn, todo_id)
    return get_todo(conn, todo_id)  # type: ignore[return-value]


def uncomplete_todo(conn: sqlite3.Connection, todo_id: int) -> Todo:
    """Mark a todo as not completed, clearing completed_at."""
    now = _now()
    if get_todo(conn, todo_id) is None:
        raise ValueError(f"todo {todo_id} not found")
    conn.execute(
        "UPDATE todos SET is_completed = 0, completed_at = NULL, updated_at = ? WHERE id = ?",
        (now, todo_id),
    )
    conn.commit()
    return get_todo(conn, todo_id)  # type: ignore[return-value]


def update_todo(conn: sqlite3.Connection, todo_id: int, data: TodoUpdate) -> Todo:
    """Update only the fields provided in `data`."""
    if get_todo(conn, todo_id) is None:
        raise ValueError(f"todo {todo_id} not found")

    fields: list[str] = []
    params: list[object] = []

    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "tags":
            fields.append("tags = ?")
            params.append(json.dumps(value or []))
        else:
            fields.append(f"{key} = ?")
            params.append(value)

    if fields:
        fields.append("updated_at = ?")
        params.append(_now())
        params.append(todo_id)
        sql = f"UPDATE todos SET {', '.join(fields)} WHERE id = ?"
        conn.execute(sql, params)
        conn.commit()

    return get_todo(conn, todo_id)  # type: ignore[return-value]


def delete_todo(conn: sqlite3.Connection, todo_id: int) -> bool:
    """Delete a todo by id. Returns True if a row was deleted."""
    cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    return cursor.rowcount > 0


def search_todos(conn: sqlite3.Connection, query: str, *, limit: int = 20) -> list[Todo]:
    """Simple LIKE search across title and description."""
    like = f"%{query}%"
    rows = conn.execute(
        """
        SELECT * FROM todos
        WHERE title LIKE ? OR description LIKE ?
        ORDER BY is_completed ASC, priority ASC, id DESC
        LIMIT ?
        """,
        (like, like, limit),
    ).fetchall()
    return [_row_to_todo(row) for row in rows]


# ---------------------------------------------------------------------------
# Recurrence (RRULE-lite): FREQ=DAILY | FREQ=WEEKLY;BYDAY=MO,WE | FREQ=MONTHLY;BYMONTHDAY=1
# ---------------------------------------------------------------------------

_FREQ_RE = re.compile(r"FREQ=(DAILY|WEEKLY|MONTHLY)", re.IGNORECASE)
_BYDAY_RE = re.compile(r"BYDAY=([A-Z,]+)", re.IGNORECASE)
_BYMONTHDAY_RE = re.compile(r"BYMONTHDAY=(\d+)", re.IGNORECASE)


def _parse_recurrence(rule: str) -> dict:
    freq_match = _FREQ_RE.search(rule or "")
    if not freq_match:
        raise ValueError(f"unsupported recurrence_rule: {rule!r} (missing FREQ)")
    freq = freq_match.group(1).upper()
    byday: list[str] = []
    byday_match = _BYDAY_RE.search(rule)
    if byday_match:
        byday = [d.strip().upper() for d in byday_match.group(1).split(",") if d.strip()]
    bymonthday: int | None = None
    bymonthday_match = _BYMONTHDAY_RE.search(rule)
    if bymonthday_match:
        bymonthday = int(bymonthday_match.group(1))
    return {"freq": freq, "byday": byday, "bymonthday": bymonthday}


def _next_due_date(rule: str, base: date) -> str:
    """Compute the next due date after *base* per the RRULE-lite *rule*."""
    parsed = _parse_recurrence(rule)
    freq = parsed["freq"]

    if freq == "DAILY":
        return (base + timedelta(days=1)).isoformat()

    if freq == "WEEKLY":
        byday = parsed["byday"]
        if not byday:
            return (base + timedelta(days=7)).isoformat()
        wanted = {_WEEKDAY_CODES.index(code) for code in byday if code in _WEEKDAY_CODES}
        if not wanted:
            return (base + timedelta(days=7)).isoformat()
        for offset in range(1, 8):
            candidate = base + timedelta(days=offset)
            if candidate.weekday() in wanted:
                return candidate.isoformat()
        return (base + timedelta(days=7)).isoformat()

    if freq == "MONTHLY":
        day = parsed["bymonthday"] or base.day
        year, month = base.year, base.month + 1
        if month > 12:
            month = 1
            year += 1
        # Clamp to the last valid day of the target month (e.g. day=31 in
        # a 30-day month) rather than raising.
        while True:
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                day -= 1
                if day < 1:
                    raise

    raise ValueError(f"unsupported recurrence frequency: {freq!r}")


def expand_recurring_todo(conn: sqlite3.Connection, todo_id: int) -> Todo | None:
    """Materialize the next instance of a recurring todo.

    The new instance carries ``parent_todo_id`` pointing at the original
    template and inherits title, priority, tags, domain, goal_id, jira_ref,
    and recurrence_rule. Idempotent: if an instance with the same
    ``(parent_todo_id, due_date)`` already exists, that existing row is
    returned instead of creating a duplicate. Returns None if the todo does
    not exist or has no ``recurrence_rule``.
    """
    template = get_todo(conn, todo_id)
    if template is None or not template.recurrence_rule:
        return None

    base_date_str = template.due_date or date.today().isoformat()
    try:
        base_date = date.fromisoformat(base_date_str)
    except ValueError:
        base_date = date.today()

    next_due = _next_due_date(template.recurrence_rule, base_date)

    existing = conn.execute(
        "SELECT id FROM todos WHERE parent_todo_id = ? AND due_date = ?",
        (todo_id, next_due),
    ).fetchone()
    if existing:
        return get_todo(conn, existing["id"])

    data = TodoCreate(
        title=template.title,
        description=template.description,
        priority=template.priority,
        due_date=next_due,
        due_time=template.due_time,
        tags=template.tags,
        domain=template.domain,
        goal_id=template.goal_id,
        jira_ref=template.jira_ref,
        recurrence_rule=template.recurrence_rule,
        parent_todo_id=todo_id,
    )
    return add_todo(conn, data)
