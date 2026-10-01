"""End-to-end verification (phase 2g): todo CRUD lands in sb_ledger with a
CHANGELOG.md bullet, via the soft ledger_bridge wired into sb_todos
handlers.

This exercises the real cross-service path: sb_todos.handlers mutations ->
sb_todos.ledger_bridge.record -> sb_core.ledger_tools.ledger_log ->
sb_core.store.ledger.append_ledger + dual-sync to CHANGELOG.md.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sb_core import ledger_tools
from sb_core.store.db import connect
from sb_core.store.ledger import register_project, search_ledger


def _make_todos_conn() -> sqlite3.Connection:
    from sb_todos.db import run_migrations as todos_migrate

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    todos_migrate(conn)
    return conn


@pytest.fixture
def core_db_path(tmp_path: Path) -> Path:
    return tmp_path / "core.db"


@pytest.fixture
def changelog_path(tmp_path: Path) -> Path:
    return tmp_path / "project" / "CHANGELOG.md"


@pytest.fixture(autouse=True)
def _patch_core_conn(monkeypatch, core_db_path):
    """Point the ledger_bridge's eventual ledger_tools.ledger_log call at
    our temp core DB instead of the real production ``core.db``."""
    monkeypatch.setattr(ledger_tools, "_get_conn", lambda: connect(core_db_path))


@pytest.fixture(autouse=True)
def _enroll_sb_project(core_db_path, changelog_path):
    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(core_db_path)
    try:
        register_project(
            conn,
            project="sb",
            root_path=str(changelog_path.parent),
            changelog_path=str(changelog_path),
            sync_mode="dual",
        )
    finally:
        conn.close()


def test_todo_add_and_complete_land_in_ledger_and_changelog(
    core_db_path: Path, changelog_path: Path
) -> None:
    from sb_todos import handlers
    from sb_todos.models import TodoCreate

    todos_conn = _make_todos_conn()
    try:
        todo = handlers.add_todo(
            todos_conn,
            TodoCreate(
                title="Test task",
                external_source="e2e-test",
                external_ref="task-1",
            ),
        )
        handlers.complete_todo(todos_conn, todo.id)
    finally:
        todos_conn.close()

    core_conn = connect(core_db_path)
    try:
        entries = search_ledger(core_conn, project="sb")
    finally:
        core_conn.close()

    assert len(entries) == 2
    verbs = {e["action_verb"] for e in entries}
    assert verbs == {"Added", "Completed"}
    summaries = {e["summary"] for e in entries}
    assert summaries == {
        'Added todo "Test task"',
        'Completed todo "Test task"',
    }
    for entry in entries:
        assert any(r.get("kind") == "todo" for r in entry["refs"])

    changelog_text = changelog_path.read_text(encoding="utf-8")
    assert 'Added todo "Test task"' in changelog_text
    assert 'Completed todo "Test task"' in changelog_text
    # Two distinct timestamped bullets, time-prefix format.
    assert changelog_text.count("UTC") >= 2


def test_rerunning_todo_add_with_same_external_ref_does_not_duplicate(
    core_db_path: Path,
) -> None:
    from sb_todos import handlers
    from sb_todos.models import TodoCreate

    todos_conn = _make_todos_conn()
    try:
        handlers.add_todo(
            todos_conn,
            TodoCreate(
                title="Test task",
                external_source="e2e-test",
                external_ref="task-1",
            ),
        )
        # Re-add with the same external_source/external_ref: idempotent
        # upsert, must not create a second ledger row.
        handlers.add_todo(
            todos_conn,
            TodoCreate(
                title="Test task",
                external_source="e2e-test",
                external_ref="task-1",
            ),
        )
    finally:
        todos_conn.close()

    core_conn = connect(core_db_path)
    try:
        entries = search_ledger(core_conn, project="sb", verb="Added")
    finally:
        core_conn.close()

    assert len(entries) == 1
