"""Tests for scheduler.py: cron parsing and run_due_schedules."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import pytest

import sb_core.scheduler as sched
from sb_core.store.db import connect


def _patch_conn(monkeypatch, db_path: Path) -> None:
    monkeypatch.setattr(sched, "_get_conn", lambda: connect(db_path))


# ---------------------------------------------------------------------------
# cron parsing
# ---------------------------------------------------------------------------


def test_cron_matches_exact_fields() -> None:
    # 0 16 * * 5  -> Friday at 16:00
    friday_4pm = datetime(2026, 10, 2, 16, 0)  # a Friday
    assert friday_4pm.weekday() == 4
    assert sched.cron_matches("0 16 * * 5", friday_4pm) is True


def test_cron_does_not_match_wrong_minute() -> None:
    friday_4pm = datetime(2026, 10, 2, 16, 1)
    assert sched.cron_matches("0 16 * * 5", friday_4pm) is False


def test_cron_does_not_match_wrong_day_of_week() -> None:
    saturday_4pm = datetime(2026, 10, 3, 16, 0)
    assert sched.cron_matches("0 16 * * 5", saturday_4pm) is False


def test_cron_wildcard_matches_every_field() -> None:
    assert sched.cron_matches("* * * * *", datetime(2026, 1, 1, 0, 0)) is True


def test_cron_step_value() -> None:
    # */15 -> :00, :15, :30, :45
    assert sched.cron_matches("*/15 * * * *", datetime(2026, 1, 1, 12, 15)) is True
    assert sched.cron_matches("*/15 * * * *", datetime(2026, 1, 1, 12, 20)) is False


def test_cron_comma_list() -> None:
    assert sched.cron_matches("0 8,16 * * *", datetime(2026, 1, 1, 16, 0)) is True
    assert sched.cron_matches("0 8,16 * * *", datetime(2026, 1, 1, 12, 0)) is False


def test_cron_range() -> None:
    assert sched.cron_matches("0 9-17 * * *", datetime(2026, 1, 1, 12, 0)) is True
    assert sched.cron_matches("0 9-17 * * *", datetime(2026, 1, 1, 20, 0)) is False


def test_parse_cron_requires_five_fields() -> None:
    with pytest.raises(ValueError):
        sched.parse_cron("0 16 * *")


def test_last_scheduled_at_finds_recent_match() -> None:
    now = datetime(2026, 10, 2, 16, 3)  # Friday, 3 minutes after the fire time
    result = sched.last_scheduled_at("0 16 * * 5", now)
    assert result == datetime(2026, 10, 2, 16, 0)


def test_last_scheduled_at_returns_none_for_impossible_cron() -> None:
    # Feb 30th never exists.
    result = sched.last_scheduled_at("0 0 30 2 *", datetime(2026, 3, 1, 0, 0), lookback_minutes=60)
    assert result is None


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


def test_scheduler_tools_are_registered_and_mounted() -> None:
    names = {t.name for t in asyncio.run(sched.mcp.list_tools())}
    expected = {
        "add_scheduled_ritual",
        "list_scheduled_rituals",
        "delete_scheduled_ritual",
        "run_due_schedules",
    }
    assert expected <= names

    from sb_core.mcp_app import mcp as parent

    mounted = {t.name for t in asyncio.run(parent.list_tools())}
    assert "run_due_schedules" in mounted


def test_add_scheduled_ritual_and_list(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    created = sched.add_scheduled_ritual(
        name="Friday wrap", ritual="wrap_day", cron="0 16 * * 5"
    )
    assert created["ritual"] == "wrap_day"
    assert created["enabled"] is True

    rows = sched.list_scheduled_rituals()
    assert len(rows) == 1
    assert rows[0]["name"] == "Friday wrap"


def test_add_scheduled_ritual_rejects_unknown_ritual(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    with pytest.raises(ValueError):
        sched.add_scheduled_ritual(name="bad", ritual="nonexistent_ritual", cron="* * * * *")


def test_add_scheduled_ritual_rejects_bad_cron(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    with pytest.raises(ValueError):
        sched.add_scheduled_ritual(name="bad", ritual="wrap_day", cron="not a cron")


def test_delete_scheduled_ritual(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    created = sched.add_scheduled_ritual(name="temp", ritual="standup", cron="* * * * *")
    result = sched.delete_scheduled_ritual(created["id"])
    assert result["deleted"] is True
    assert sched.list_scheduled_rituals() == []


def test_run_due_schedules_runs_matching_ritual(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    # Always-matching cron so it is due immediately regardless of "now".
    sched.add_scheduled_ritual(name="always", ritual="standup", cron="* * * * *")

    called = {"count": 0}

    def _fake_standup(**kwargs):
        called["count"] += 1
        return {"date": "2026-09-30", "bullets": []}

    monkeypatch.setattr(sched, "_ritual_dispatch", lambda: {"standup": _fake_standup})

    result = sched.run_due_schedules()
    assert called["count"] == 1
    assert result["outcomes"]["always"]["ran"] is True
    assert result["outcomes"]["always"]["status"] == "ok"

    rows = sched.list_scheduled_rituals()
    assert rows[0]["last_status"] == "ok"
    assert rows[0]["last_run_at"] is not None


def test_run_due_schedules_is_idempotent_within_same_minute(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    sched.add_scheduled_ritual(name="always", ritual="standup", cron="* * * * *")

    called = {"count": 0}

    def _fake_standup(**kwargs):
        called["count"] += 1
        return {}

    monkeypatch.setattr(sched, "_ritual_dispatch", lambda: {"standup": _fake_standup})
    # Pin "now" so both calls evaluate to the exact same fire-minute.
    fixed_now = sched._now_local()
    monkeypatch.setattr(sched, "_now_local", lambda: fixed_now)

    sched.run_due_schedules()
    sched.run_due_schedules()
    assert called["count"] == 1


def test_run_due_schedules_skips_disabled(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    sched.add_scheduled_ritual(name="disabled", ritual="standup", cron="* * * * *", enabled=False)

    called = {"count": 0}
    monkeypatch.setattr(
        sched, "_ritual_dispatch", lambda: {"standup": lambda **kw: called.update(count=called["count"] + 1)}
    )

    result = sched.run_due_schedules()
    assert called["count"] == 0
    assert result["outcomes"] == {}


def test_run_due_schedules_records_error_status_without_raising(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    sched.add_scheduled_ritual(name="broken", ritual="wrap_day", cron="* * * * *")

    def _raise(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(sched, "_ritual_dispatch", lambda: {"wrap_day": _raise})

    result = sched.run_due_schedules()
    assert result["outcomes"]["broken"]["status"] == "error"
    assert "boom" in result["outcomes"]["broken"]["error"]
