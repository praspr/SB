"""Tests for the soft todo -> sb-core ledger bridge (phase 2g)."""

from __future__ import annotations

import sys
import types

import pytest

from sb_todos import handlers, ledger_bridge
from sb_todos.models import TodoCreate, TodoUpdate


# ---------------------------------------------------------------------------
# ledger_bridge.record() itself
# ---------------------------------------------------------------------------


def _install_fake_sb_core(monkeypatch, ledger_log_fn):
    """Install a fake ``sb_core.ledger_tools`` module so ``record()`` can
    import it without sb-core actually being installed in this venv."""
    fake_ledger_tools = types.ModuleType("sb_core.ledger_tools")
    fake_ledger_tools.ledger_log = ledger_log_fn
    fake_sb_core = types.ModuleType("sb_core")
    fake_sb_core.ledger_tools = fake_ledger_tools
    monkeypatch.setitem(sys.modules, "sb_core", fake_sb_core)
    monkeypatch.setitem(sys.modules, "sb_core.ledger_tools", fake_ledger_tools)


def test_record_calls_ledger_log_with_expected_fields(monkeypatch):
    calls = []

    def fake_ledger_log(**kwargs):
        calls.append(kwargs)
        return {"id": 1, "was_new": True}

    _install_fake_sb_core(monkeypatch, fake_ledger_log)

    ledger_bridge.record(
        "Added",
        'Added todo "Test task"',
        None,
        [{"kind": "todo", "value": "42"}],
    )

    assert len(calls) == 1
    kwargs = calls[0]
    assert kwargs["project"] == "sb"
    assert kwargs["action_verb"] == "Added"
    assert kwargs["summary"] == 'Added todo "Test task"'
    assert kwargs["refs"] == [{"kind": "todo", "value": "42"}]
    assert kwargs["agent"] == "todos-service"
    assert kwargs["source_harness"] == "todos-mcp"
    assert "working_dir" in kwargs


def test_record_swallows_import_errors(monkeypatch, caplog):
    # sb_core genuinely not importable in this environment by default;
    # ensure no exception propagates.
    monkeypatch.delitem(sys.modules, "sb_core", raising=False)
    monkeypatch.delitem(sys.modules, "sb_core.ledger_tools", raising=False)

    with caplog.at_level("WARNING"):
        ledger_bridge.record("Added", "Added todo \"x\"", None, [])
    # No exception raised is the main assertion; a warning may or may not
    # be captured depending on import machinery, but the call must return.


def test_record_swallows_ledger_log_errors(monkeypatch, caplog):
    def failing_ledger_log(**kwargs):
        raise RuntimeError("db is locked")

    _install_fake_sb_core(monkeypatch, failing_ledger_log)

    with caplog.at_level("WARNING"):
        ledger_bridge.record("Added", 'Added todo "x"', None, [])

    assert any("ledger bridge failed" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# Handler wiring: each mutation fires exactly one record() call
# ---------------------------------------------------------------------------


@pytest.fixture
def recorded(monkeypatch):
    calls = []
    monkeypatch.setattr(
        handlers.ledger_bridge,
        "record",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    return calls


def test_todo_add_records_once(conn, recorded):
    handlers.add_todo(conn, TodoCreate(title="Test task"))
    assert len(recorded) == 1
    args, _ = recorded[0]
    verb, summary, body, refs = args
    assert verb == "Added"
    assert summary == 'Added todo "Test task"'
    assert body is None
    assert refs[0]["kind"] == "todo"


def test_todo_add_idempotent_upsert_skips_record(conn, recorded):
    handlers.add_todo(
        conn,
        TodoCreate(title="Synced task", external_source="jira", external_ref="ABC-1"),
    )
    assert len(recorded) == 1
    recorded.clear()

    # Same external_source/external_ref -> upsert, no-op for the ledger.
    handlers.add_todo(
        conn,
        TodoCreate(title="Synced task", external_source="jira", external_ref="ABC-1"),
    )
    assert recorded == []


def test_todo_complete_records_once(conn, recorded):
    todo = handlers.add_todo(conn, TodoCreate(title="Finish me"))
    recorded.clear()

    handlers.complete_todo(conn, todo.id)
    assert len(recorded) == 1
    args, _ = recorded[0]
    verb, summary, body, refs = args
    assert verb == "Completed"
    assert summary == 'Completed todo "Finish me"'
    assert refs == [{"kind": "todo", "value": str(todo.id)}]


def test_todo_uncomplete_records_once(conn, recorded):
    todo = handlers.add_todo(conn, TodoCreate(title="Reopen me"))
    handlers.complete_todo(conn, todo.id)
    recorded.clear()

    handlers.uncomplete_todo(conn, todo.id)
    assert len(recorded) == 1
    args, _ = recorded[0]
    verb, summary, _, _ = args
    assert verb == "Reopened"
    assert summary == 'Reopened todo "Reopen me"'


def test_todo_update_records_with_diff(conn, recorded):
    todo = handlers.add_todo(conn, TodoCreate(title="Needs edit", priority=2))
    recorded.clear()

    handlers.update_todo(conn, todo.id, TodoUpdate(priority=1, due_date="2026-10-05"))
    assert len(recorded) == 1
    args, _ = recorded[0]
    verb, summary, body, _ = args
    assert verb == "Updated"
    assert summary == 'Updated todo "Needs edit"'
    assert "priority 2" in body
    assert "due_date" in body


def test_todo_delete_records_once(conn, recorded):
    todo = handlers.add_todo(conn, TodoCreate(title="Delete me"))
    recorded.clear()

    result = handlers.delete_todo(conn, todo.id)
    assert result is True
    assert len(recorded) == 1
    args, _ = recorded[0]
    verb, summary, _, _ = args
    assert verb == "Removed"
    assert summary == 'Removed todo "Delete me"'


def test_todo_delete_missing_id_no_record(conn, recorded):
    result = handlers.delete_todo(conn, 999999)
    assert result is False
    assert recorded == []
