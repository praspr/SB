"""Adapter: emit task signals from the sb_todos SQLite DB.

Uses in-process handlers (no HTTP).  Accepts an optional ``todos_conn``
for test isolation; falls back to the shared singleton.

In addition to the per-todo signal upsert, completed todos get a backup
promotion into ``sb_ledger`` via ``_promote_to_ledger``. This is a safety
net only: real-time logging happens via ``sb_todos.ledger_bridge`` at
mutation time (phase 2g). This path exists in case that soft import ever
fails silently, or the raw todos service is used outside sb-core without
the bridge wired up. It is idempotent via ``content_sha256`` so running it
alongside the real-time bridge never double-logs.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from sb_todos.handlers import list_todos

from ..store.signals import upsert_signal

logger = logging.getLogger(__name__)


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
        if todo.is_completed and todo.completed_at:
            try:
                _promote_to_ledger(core_conn, todo)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "todos adapter: failed to promote ledger entry for todo %s: %s",
                    todo.id,
                    exc,
                )
    return count


def _promote_to_ledger(core_conn: sqlite3.Connection, todo) -> None:
    """Backup promotion of a completed todo into ``sb_ledger``.

    Only fires for completed todos. Idempotent via ``content_sha256`` (see
    ``store.ledger.append_ledger``): if the real-time bridge already wrote
    this exact entry, this is a no-op.
    """
    from ..store.ledger import append_ledger

    summary = f'Completed todo "{todo.title}"'
    refs = [{"kind": "todo", "value": str(todo.id)}]
    if todo.jira_ref:
        refs.append({"kind": "jira", "value": todo.jira_ref})

    append_ledger(
        core_conn,
        project="sb",
        summary=summary,
        action_verb="Completed",
        refs=refs,
        agent="todos-adapter",
        source_harness="todos-adapter",
        origin="adapter-promote-backup",
        ts=_to_ledger_ts(todo.completed_at),
    )


def _to_ledger_ts(completed_at: str) -> str:
    """Best-effort normalization of sb_todos' ``YYYY-MM-DD HH:MM:SS`` (UTC,
    no offset) completed_at into the ledger's ``YYYY-MM-DDTHH:MM:SSZ`` form.
    Falls back to passing the value through unchanged if it doesn't match.
    """
    value = completed_at.strip()
    if "T" in value or value.endswith("Z"):
        return value
    if " " in value:
        date_part, time_part = value.split(" ", 1)
        return f"{date_part}T{time_part}Z"
    return value
