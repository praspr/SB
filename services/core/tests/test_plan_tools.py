"""Plan tools persist plan columns without overwriting wrap."""

from __future__ import annotations

from pathlib import Path

import pytest

import sb_core.plan_tools as plan
from sb_core.store import daily as daily_store
from sb_core.store.db import connect as core_connect
from sb_core.store.signals import upsert_signal

DATE = "2026-09-30"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from sb_todos.db import connect as todos_connect

    core_db = tmp_path / "core.db"
    todos_db = tmp_path / "todos.db"
    core_connect(core_db).close()
    todos_connect(todos_db).close()
    monkeypatch.setattr(plan, "_get_conn", lambda: core_connect(core_db))
    monkeypatch.setattr(plan, "_get_todos_conn", lambda: todos_connect(todos_db))
    monkeypatch.setattr(plan, "_today", lambda: DATE)
    monkeypatch.setattr(
        plan,
        "_load_goals",
        lambda active_only=True: {"contractual": [], "quarterly": [], "weekly": []},
    )
    return {"core_db": core_db, "todos_db": todos_db}


def _add_todo(todos_db: Path, **kwargs) -> int:
    from sb_todos import handlers
    from sb_todos.db import connect as todos_connect
    from sb_todos.models import TodoCreate

    conn = todos_connect(todos_db)
    try:
        return handlers.add_todo(conn, TodoCreate(**kwargs)).id
    finally:
        conn.close()


def test_plan_day_persists_ranks_and_keeps_wrap(env) -> None:
    _add_todo(env["todos_db"], title="Ship the release", priority=1)
    _add_todo(env["todos_db"], title="Tidy notes", priority=4)
    conn = core_connect(env["core_db"])
    daily_store.save_wrap(conn, DATE, "WRAP", {"signal_ids": [9]})
    conn.close()

    result = plan.plan_day()
    assert result["date"] == DATE
    assert "Ship the release" in result["plan_md"]
    assert result["cached"] is False

    again = plan.plan_day()
    assert again["cached"] is True
    refreshed = plan.plan_day(refresh=True)
    assert refreshed["cached"] is False

    conn = core_connect(env["core_db"])
    try:
        saved = daily_store.get_daily(conn, DATE)
    finally:
        conn.close()
    assert saved["wrap_md"] == "WRAP"
    assert saved["plan_md"]


def test_plan_cites_signals_and_get_day_round_trips(env) -> None:
    _add_todo(env["todos_db"], title="Investigate outage", priority=1)
    conn = core_connect(env["core_db"])
    try:
        upsert_signal(
            conn,
            source="git",
            source_id="c1",
            kind="commit",
            occurred_at=f"{DATE}T09:00:00Z",
            title="fix: patch outage",
        )
    finally:
        conn.close()
    result = plan.plan_day()
    assert "[signal:" in result["plan_md"]
    loaded = plan.get_day()
    assert "Investigate outage" in loaded["plan_md"]


def test_invalid_plan_date_raises(env) -> None:
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        plan.plan_day(date="09/30/2026")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        plan.get_day(date="2026-13-40")


def test_whoami_and_goals(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sb_core.config import settings

    monkeypatch.setattr(settings, "identity_name", "Jane")
    monkeypatch.setattr(settings, "identity_email", "jane@example.com")
    monkeypatch.setattr(settings, "goals_path", tmp_path / "missing.yaml")
    assert plan.whoami() == {"name": "Jane", "email": "jane@example.com"}
    goals = plan.get_goals()
    assert goals == {"contractual": [], "quarterly": [], "weekly": []}
