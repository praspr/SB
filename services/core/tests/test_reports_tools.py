"""Exercise the 4 report MCP tools via monkeypatched _get_conn."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path

import sb_core.reports_tools as rt
from sb_core.store.db import connect
from sb_core.store.ledger import append_ledger


def _patch_conn(monkeypatch, db_path: Path) -> None:
    monkeypatch.setattr(rt, "_get_conn", lambda: connect(db_path))


def test_all_four_tools_are_registered() -> None:
    tools = asyncio.run(rt.mcp.list_tools())
    names = {t.name for t in tools}
    assert {
        "report_daily",
        "report_weekly",
        "report_monthly",
        "report_query",
        "report_perf_checkin",
    } <= names


def test_reports_tools_are_mounted_on_parent_mcp() -> None:
    from sb_core.mcp_app import mcp as parent

    tools = asyncio.run(parent.list_tools())
    names = {t.name for t in tools}
    assert "report_daily" in names
    assert "report_query" in names


def test_report_daily_returns_markdown_shape(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    conn = connect(db_path)
    try:
        yesterday = date(2026, 9, 29)
        append_ledger(
            conn,
            project="sb",
            summary="Shipped the reports backend",
            action_verb="Shipped",
            ts=f"{yesterday.isoformat()}T09:00:00Z",
        )
    finally:
        conn.close()

    result = rt.report_daily(date="2026-09-30")
    assert "markdown" in result
    assert "Shipped the reports backend" in result["markdown"]
    assert "range" in result


def test_report_daily_rejects_bad_date() -> None:
    result = rt.report_daily(date="not-a-date")
    assert "error" in result
    assert "not-a-date" in result["error"]


def test_report_weekly_returns_markdown_shape(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    conn = connect(db_path)
    try:
        append_ledger(
            conn,
            project="sb",
            summary="Weekly entry",
            action_verb="Shipped",
            ts="2026-09-28T09:00:00Z",
        )
    finally:
        conn.close()

    result = rt.report_weekly(week_end="2026-09-30")
    assert "Weekly entry" in result["markdown"]
    assert "## Verb frequency" in result["markdown"]


def test_report_weekly_rejects_bad_week_end() -> None:
    result = rt.report_weekly(week_end="2026/09/30")
    assert "error" in result


def test_report_monthly_returns_markdown_shape(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    conn = connect(db_path)
    try:
        append_ledger(
            conn,
            project="sb",
            summary="Monthly entry",
            action_verb="Shipped",
            ts="2026-09-15T09:00:00Z",
        )
    finally:
        conn.close()

    result = rt.report_monthly(month="2026-09")
    assert "Monthly entry" in result["markdown"]
    assert "## Week" in result["markdown"]


def test_report_monthly_rejects_bad_month() -> None:
    result = rt.report_monthly(month="September-2026")
    assert "error" in result


def test_report_query_deterministic_by_default(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    conn = connect(db_path)
    try:
        append_ledger(
            conn,
            project="sb",
            summary="Debugged the reports query tool",
            action_verb="Debugged",
            ts="2026-09-30T09:00:00Z",
        )
    finally:
        conn.close()

    result = rt.report_query(q="reports")
    assert "Debugged the reports query tool" in result["markdown"]
    assert result["citations"]


def test_report_query_with_project_filter(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    conn = connect(db_path)
    try:
        append_ledger(conn, project="sb", summary="sb thing about widgets", action_verb="Shipped", ts="2026-09-30T09:00:00Z")
        append_ledger(conn, project="ciq", summary="ciq thing about widgets", action_verb="Shipped", ts="2026-09-30T09:00:00Z")
    finally:
        conn.close()

    result = rt.report_query(q="widgets", project="sb")
    assert "sb thing about widgets" in result["markdown"]
    assert "ciq thing about widgets" not in result["markdown"]


# ---------------------------------------------------------------------------
# report_perf_checkin
# ---------------------------------------------------------------------------


def test_report_perf_checkin_calls_perf_checkin_with_validated_args(monkeypatch) -> None:
    captured = {}

    def _fake_perf_checkin(*, shape, voice):
        captured["shape"] = shape
        captured["voice"] = voice
        return {"markdown": "ok", "citations": [], "range": {}, "shape": shape, "voice": voice}

    monkeypatch.setattr(rt, "_perf_checkin", _fake_perf_checkin)

    result = rt.report_perf_checkin(shape="one-improvement", voice="third-person")
    assert captured == {"shape": "one-improvement", "voice": "third-person"}
    assert result["markdown"] == "ok"


def test_report_perf_checkin_defaults_to_full_first_person(monkeypatch) -> None:
    captured = {}

    def _fake_perf_checkin(*, shape, voice):
        captured["shape"] = shape
        captured["voice"] = voice
        return {"markdown": "ok"}

    monkeypatch.setattr(rt, "_perf_checkin", _fake_perf_checkin)

    rt.report_perf_checkin()
    assert captured == {"shape": "full", "voice": "first-person"}


def test_report_perf_checkin_rejects_bad_shape() -> None:
    result = rt.report_perf_checkin(shape="partial")
    assert "error" in result
    assert "shape" in result["error"]


def test_report_perf_checkin_rejects_bad_voice() -> None:
    result = rt.report_perf_checkin(voice="robot")
    assert "error" in result
    assert "voice" in result["error"]
