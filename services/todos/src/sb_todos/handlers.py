"""Pure handler functions shared by MCP tools and REST routes.

Every handler takes a sqlite3.Connection as first argument, plus keyword
arguments describing the operation. Handlers return Pydantic models (or
lists/bools) and never touch transport concerns (HTTP, MCP protocol, etc).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .models import Todo, TodoCreate, TodoUpdate


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
                  due_time = ?, tags = ?, domain = ?, updated_at = ?
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
          external_source, external_ref, domain, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            now,
            now,
        ),
    )
    conn.commit()
    todo_id = cursor.lastrowid
    return get_todo(conn, todo_id)  # type: ignore[return-value]


def complete_todo(conn: sqlite3.Connection, todo_id: int) -> Todo:
    """Mark a todo as completed, setting completed_at and updated_at to now."""
    now = _now()
    if get_todo(conn, todo_id) is None:
        raise ValueError(f"todo {todo_id} not found")
    conn.execute(
        "UPDATE todos SET is_completed = 1, completed_at = ?, updated_at = ? WHERE id = ?",
        (now, now, todo_id),
    )
    conn.commit()
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
