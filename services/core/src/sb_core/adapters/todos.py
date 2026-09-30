"""Adapter: emit task signals from the sb_todos SQLite DB.

Uses in-process handlers (no HTTP).  Accepts an optional ``todos_conn``
for test isolation; falls back to the shared singleton.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from sb_todos.handlers import list_todos

from ..store.signals import upsert_signal


def run(
    core_conn: sqlite3.Connection,
    *,
    todos_conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Emit one 'task' signal per todo. Returns the count upserted."""
    if todos_conn is None:
        from sb_todos.db import get_conn

        todos_conn = get_conn()

    todos = list_todos(todos_conn, status="all", limit=10_000)
    count = 0
    for todo in todos:
        upsert_signal(
            core_conn,
            source="todos",
            source_id=str(todo.id),
            kind="task",
            occurred_at=todo.created_at,
            title=todo.title,
            body=todo.description or None,
            scope=todo.domain,
            refs=[],
        )
        count += 1
    return count
