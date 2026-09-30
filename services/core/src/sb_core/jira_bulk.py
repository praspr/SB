"""Bulk-import local JIRA tickets into sb-todos as manual copies for triage.

Read-only against Atlassian (works entirely off the local markdown mirror,
same as every other ``sb_jira`` tool). Idempotent via ``todo_add``'s
existing ``external_source='jira'`` / ``external_ref=<key>`` upsert.
"""

from __future__ import annotations

from typing import Optional

from fastmcp import FastMCP

mcp = FastMCP(
    "sb-jira-bulk",
    instructions=(
        "Bulk-import JIRA tickets from the local mirror into sb-todos. "
        "Read-only against Atlassian; writes only local todos."
    ),
)

_PRIORITY_MAP = {
    "highest": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "lowest": 4,
}


def _map_priority(jira_priority: str) -> int:
    return _PRIORITY_MAP.get((jira_priority or "").strip().lower(), 3)


@mcp.tool()
def bulk_import_jira_to_todos(
    project: Optional[str] = None,
    statuses: Optional[list[str]] = None,
    dry_run: bool = False,
) -> dict:
    """Create a sb-todos entry for each local-mirror JIRA ticket matching
    the filters.

    Idempotent: each todo is created with ``external_source='jira'`` and
    ``external_ref=<key>``, so re-running updates the existing todo instead
    of duplicating it (see ``sb_todos.handlers.add_todo``). The new
    ``jira_ref`` column is also populated with the ticket key.

    Args:
        project: Exact project key filter, e.g. ``"CXP"``. ``None`` for all.
        statuses: Exact status allow-list, e.g. ``["Open", "In Progress"]``.
            ``None`` means no status filter.
        dry_run: When True, compute the would-be result without writing any
            todos.

    Returns:
        ``{"imported": int, "skipped": int, "ticket_keys": [...]}``.
    """
    from sb_jira import file_store

    tickets = [file_store.to_ticket(d) for d in file_store.load_all()]
    if project:
        tickets = [t for t in tickets if t.project == project]
    if statuses:
        allowed = set(statuses)
        tickets = [t for t in tickets if t.status in allowed]

    imported = 0
    skipped = 0
    ticket_keys: list[str] = []

    if not dry_run:
        from sb_todos import handlers as todo_handlers
        from sb_todos.config import settings as todo_settings
        from sb_todos.db import connect as connect_todos
        from sb_todos.models import TodoCreate

        todos_conn = connect_todos(todo_settings.db_path)
        try:
            for ticket in tickets:
                try:
                    todo_handlers.add_todo(
                        todos_conn,
                        TodoCreate(
                            title=f"{ticket.key}: {ticket.title}",
                            description=ticket.description or "",
                            priority=_map_priority(ticket.priority),
                            external_source="jira",
                            external_ref=ticket.key,
                            jira_ref=ticket.key,
                        ),
                    )
                    imported += 1
                    ticket_keys.append(ticket.key)
                except Exception:  # noqa: BLE001
                    skipped += 1
        finally:
            todos_conn.close()
    else:
        imported = len(tickets)
        ticket_keys = [t.key for t in tickets]

    return {"imported": imported, "skipped": skipped, "ticket_keys": ticket_keys}
