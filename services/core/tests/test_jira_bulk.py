"""Tests for jira_bulk.py: bulk_import_jira_to_todos against a fixture
tickets directory, writing into an isolated todos DB."""

from __future__ import annotations

from pathlib import Path

import pytest

from sb_core.jira_bulk import bulk_import_jira_to_todos


def _write_ticket(
    tickets_dir: Path,
    key: str,
    *,
    project: str,
    title: str,
    status: str,
    priority: str,
) -> None:
    tickets_dir.mkdir(parents=True, exist_ok=True)
    site = "cisco-cxe.atlassian.net"
    text = f"""# {key} — {title}

| Field | Value |
|-------|-------|
| **Key** | [{key}](https://{site}/browse/{key}) |
| **Status** | {status} |
| **Priority** | {priority} |
| **Type** | Bug |
| **Assignee** | PRASAD P R |
| **Created** | 2026-09-01 |
| **Updated** | 2026-09-02 |

---

## Context

Fixture ticket for jira_bulk tests.
"""
    (tickets_dir / f"{key}.md").write_text(text, encoding="utf-8")


@pytest.fixture
def tickets_dir(tmp_path, monkeypatch) -> Path:
    from sb_jira.config import settings as jira_settings

    directory = tmp_path / "tickets"
    directory.mkdir()
    monkeypatch.setattr(jira_settings, "tickets_dir", directory)
    return directory


@pytest.fixture
def todos_db(tmp_path, monkeypatch) -> Path:
    from sb_todos.config import settings as todo_settings

    db_path = tmp_path / "todos.db"
    monkeypatch.setattr(todo_settings, "db_path", db_path)
    return db_path


def test_dry_run_computes_result_without_writing_todos(tickets_dir, todos_db) -> None:
    _write_ticket(
        tickets_dir, "CXP-1", project="CXP", title="Fix the thing", status="Open", priority="High"
    )

    result = bulk_import_jira_to_todos(dry_run=True)
    assert result["imported"] == 1
    assert result["ticket_keys"] == ["CXP-1"]

    from sb_todos import handlers as todo_handlers
    from sb_todos.db import connect as connect_todos

    conn = connect_todos(todos_db)
    try:
        todos = todo_handlers.list_todos(conn, status="all", limit=100)
    finally:
        conn.close()
    assert todos == []


def test_bulk_import_creates_todos_with_priority_mapping(tickets_dir, todos_db) -> None:
    _write_ticket(tickets_dir, "CXP-1", project="CXP", title="Highest one", status="Open", priority="Highest")
    _write_ticket(tickets_dir, "CXP-2", project="CXP", title="Low one", status="Open", priority="Low")

    result = bulk_import_jira_to_todos()
    assert result["imported"] == 2
    assert set(result["ticket_keys"]) == {"CXP-1", "CXP-2"}

    from sb_todos import handlers as todo_handlers
    from sb_todos.db import connect as connect_todos

    conn = connect_todos(todos_db)
    try:
        todos = {t.jira_ref: t for t in todo_handlers.list_todos(conn, status="all", limit=100)}
    finally:
        conn.close()

    assert todos["CXP-1"].priority == 1  # Highest -> 1
    assert todos["CXP-2"].priority == 4  # Low -> 4
    assert todos["CXP-1"].external_source == "jira"
    assert todos["CXP-1"].external_ref == "CXP-1"


def test_bulk_import_is_idempotent(tickets_dir, todos_db) -> None:
    _write_ticket(tickets_dir, "CXP-1", project="CXP", title="A ticket", status="Open", priority="Medium")

    bulk_import_jira_to_todos()
    bulk_import_jira_to_todos()

    from sb_todos import handlers as todo_handlers
    from sb_todos.db import connect as connect_todos

    conn = connect_todos(todos_db)
    try:
        todos = todo_handlers.list_todos(conn, status="all", limit=100)
    finally:
        conn.close()
    assert len(todos) == 1


def test_bulk_import_filters_by_project(tickets_dir, todos_db) -> None:
    _write_ticket(tickets_dir, "CXP-1", project="CXP", title="In scope", status="Open", priority="Medium")
    _write_ticket(tickets_dir, "OTHER-1", project="OTHER", title="Out of scope", status="Open", priority="Medium")

    result = bulk_import_jira_to_todos(project="CXP")
    assert result["ticket_keys"] == ["CXP-1"]


def test_bulk_import_filters_by_statuses(tickets_dir, todos_db) -> None:
    _write_ticket(tickets_dir, "CXP-1", project="CXP", title="Open one", status="Open", priority="Medium")
    _write_ticket(tickets_dir, "CXP-2", project="CXP", title="Closed one", status="Closed", priority="Medium")

    result = bulk_import_jira_to_todos(statuses=["Open"])
    assert result["ticket_keys"] == ["CXP-1"]


def test_bulk_import_medium_maps_to_priority_3(tickets_dir, todos_db) -> None:
    _write_ticket(tickets_dir, "CXP-1", project="CXP", title="Medium", status="Open", priority="Medium")
    bulk_import_jira_to_todos()

    from sb_todos import handlers as todo_handlers
    from sb_todos.db import connect as connect_todos

    conn = connect_todos(todos_db)
    try:
        todo = todo_handlers.list_todos(conn, status="all", limit=100)[0]
    finally:
        conn.close()
    assert todo.priority == 3
