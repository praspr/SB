"""Adapter: emit ticket signals from the local JIRA markdown mirror.

Read-only — never contacts Atlassian; uses sb_jira.file_store only.
Accepts an optional ``tickets_dir`` for test isolation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from sb_jira import file_store

from ..store.signals import upsert_signal


def run(
    core_conn: sqlite3.Connection,
    *,
    tickets_dir: Optional[Path] = None,
) -> int:
    """Emit one 'ticket' signal per JIRA markdown file. Returns the count upserted."""
    details = file_store.load_all(tickets_dir)
    count = 0
    for detail in details:
        upsert_signal(
            core_conn,
            source="jira",
            source_id=detail.key,
            kind="ticket",
            occurred_at=detail.updated or detail.created or "",
            title=f"{detail.key} {detail.title}",
            body=detail.description or None,
            scope=detail.project,
            refs=[detail.url] if detail.url else [],
            raw_ref=detail.file_path or None,
        )
        count += 1
    return count
