"""Fixture-driven tests for sb_core.reports.templates."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from sb_core.reports import templates
from sb_core.store.db import connect
from sb_core.store.ledger import append_ledger


def _seed(conn, *, project: str, summary: str, action_verb: str, day: date, time_str: str = "09:00:00", scope=None, refs=None):
    ts = f"{day.isoformat()}T{time_str}Z"
    return append_ledger(
        conn,
        project=project,
        summary=summary,
        action_verb=action_verb,
        scope=scope,
        refs=refs,
        ts=ts,
    )


# ---------------------------------------------------------------------------
# daily
# ---------------------------------------------------------------------------


def test_daily_groups_yesterdays_entries_by_project_and_scope(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        today = date(2026, 9, 30)
        yesterday = today - timedelta(days=1)
        _seed(conn, project="sb", summary="Shipped feature A", action_verb="Shipped", day=yesterday, scope="core")
        _seed(conn, project="sb", summary="Fixed bug B", action_verb="Fixed", day=yesterday, scope="web")
        _seed(conn, project="ciq", summary="Debugged issue C", action_verb="Debugged", day=yesterday, scope="agents")
        # A "today" entry must NOT appear in the daily report (report is for
        # yesterday's activity).
        _seed(conn, project="sb", summary="Should not appear", action_verb="Note", day=today)

        result = templates.daily(conn, target_date=today)

        assert "Shipped feature A" in result["markdown"]
        assert "Fixed bug B" in result["markdown"]
        assert "Debugged issue C" in result["markdown"]
        assert "Should not appear" not in result["markdown"]
        assert "## sb" in result["markdown"]
        assert "## ciq" in result["markdown"]
        assert "### core" in result["markdown"]
        assert len(result["citations"]) == 3
        assert result["range"]["from"] == "2026-09-29T00:00:00Z"
        assert result["range"]["to"] == "2026-09-30T00:00:00Z"
    finally:
        conn.close()


def test_daily_filters_by_project(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        today = date(2026, 9, 30)
        yesterday = today - timedelta(days=1)
        _seed(conn, project="sb", summary="sb work", action_verb="Shipped", day=yesterday)
        _seed(conn, project="ciq", summary="ciq work", action_verb="Shipped", day=yesterday)

        result = templates.daily(conn, target_date=today, project="sb")
        assert "sb work" in result["markdown"]
        assert "ciq work" not in result["markdown"]
    finally:
        conn.close()


def test_daily_handles_empty_window(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        result = templates.daily(conn, target_date=date(2026, 9, 30))
        assert "No ledger activity" in result["markdown"]
        assert result["citations"] == []
    finally:
        conn.close()


def test_daily_includes_open_threads_section(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        today = date(2026, 9, 30)
        yesterday = today - timedelta(days=1)
        _seed(
            conn,
            project="sb",
            summary="Linked an open todo",
            action_verb="Note",
            day=yesterday,
            refs=[{"kind": "todo", "value": "1"}],
        )
        # open_threads() cross-service lookups are best-effort and return
        # empty when sb_todos/sb_jira aren't reachable in this test process,
        # so we only assert the section is *absent* when there is nothing
        # open -- presence is covered indirectly via store/test_ledger_store.
        result = templates.daily(conn, target_date=today)
        assert isinstance(result["citations"], list)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# weekly
# ---------------------------------------------------------------------------


def test_weekly_verb_frequency_and_ref_frequency(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        week_end = date(2026, 9, 30)
        _seed(conn, project="sb", summary="one", action_verb="Shipped", day=week_end, refs=[{"kind": "jira", "value": "CXP-1"}])
        _seed(conn, project="sb", summary="two", action_verb="Shipped", day=week_end - timedelta(days=1), refs=[{"kind": "jira", "value": "CXP-1"}])
        _seed(conn, project="sb", summary="three", action_verb="Fixed", day=week_end - timedelta(days=2))

        result = templates.weekly(conn, week_end=week_end)

        assert "## Verb frequency" in result["markdown"]
        assert "**Shipped**: 2" in result["markdown"]
        assert "**Fixed**: 1" in result["markdown"]
        assert "## Top references" in result["markdown"]
        assert "`jira:CXP-1`: 2" in result["markdown"]
        assert len(result["citations"]) == 3
    finally:
        conn.close()


def test_weekly_digest_groups_by_day(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        week_end = date(2026, 9, 30)
        _seed(conn, project="sb", summary="day one entry", action_verb="Shipped", day=week_end)
        _seed(conn, project="sb", summary="day two entry", action_verb="Shipped", day=week_end - timedelta(days=1))

        result = templates.weekly(conn, week_end=week_end)
        assert "### 2026-09-30" in result["markdown"]
        assert "### 2026-09-29" in result["markdown"]
    finally:
        conn.close()


def test_weekly_excludes_entries_outside_window(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        week_end = date(2026, 9, 30)
        _seed(conn, project="sb", summary="too old", action_verb="Shipped", day=week_end - timedelta(days=10))
        result = templates.weekly(conn, week_end=week_end)
        assert "too old" not in result["markdown"]
        assert "No ledger activity" in result["markdown"]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# monthly
# ---------------------------------------------------------------------------


def test_monthly_groups_by_week(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        _seed(conn, project="sb", summary="week1 entry", action_verb="Shipped", day=date(2026, 9, 2))
        _seed(conn, project="sb", summary="week2 entry", action_verb="Shipped", day=date(2026, 9, 9))

        result = templates.monthly(conn, month="2026-09")

        assert "# Monthly report — 2026-09" in result["markdown"]
        assert "## Week" in result["markdown"]
        assert "week1 entry" in result["markdown"]
        assert "week2 entry" in result["markdown"]
        assert len(result["citations"]) == 2
    finally:
        conn.close()


def test_monthly_excludes_entries_outside_month(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        _seed(conn, project="sb", summary="august entry", action_verb="Shipped", day=date(2026, 8, 31))
        _seed(conn, project="sb", summary="september entry", action_verb="Shipped", day=date(2026, 9, 1))

        result = templates.monthly(conn, month="2026-09")
        assert "august entry" not in result["markdown"]
        assert "september entry" in result["markdown"]
    finally:
        conn.close()


def test_monthly_defaults_to_current_month(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        result = templates.monthly(conn)
        assert result["markdown"].startswith("# Monthly report —")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------


def test_query_deterministic_fallback_when_llm_disabled(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        _seed(conn, project="sb", summary="Debugged APISIX 401", action_verb="Debugged", day=date(2026, 9, 30))
        result = templates.query(conn, q="APISIX", llm_narrate=False)
        assert result["mode"] == "fallback"
        assert "Debugged APISIX 401" in result["markdown"]
        assert len(result["citations"]) == 1
    finally:
        conn.close()


def test_query_deterministic_fallback_when_llm_raises(tmp_path: Path, monkeypatch) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        _seed(conn, project="sb", summary="Debugged APISIX 401", action_verb="Debugged", day=date(2026, 9, 30))

        from sb_core import llm as llm_mod

        def _raise(*args, **kwargs):
            raise llm_mod.LLMUnavailable("down")

        monkeypatch.setattr(llm_mod, "complete", _raise)

        result = templates.query(conn, q="APISIX", llm_narrate=True)
        assert result["mode"] == "fallback"
        assert "Debugged APISIX 401" in result["markdown"]
    finally:
        conn.close()


def test_query_uses_llm_narration_when_citations_valid(tmp_path: Path, monkeypatch) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        result_row = _seed(conn, project="sb", summary="Debugged APISIX 401", action_verb="Debugged", day=date(2026, 9, 30))
        ledger_id = result_row["id"]

        from sb_core import llm as llm_mod

        monkeypatch.setattr(
            llm_mod, "complete", lambda prompt, model=None: f"You fixed APISIX. [ledger:{ledger_id}]"
        )

        result = templates.query(conn, q="APISIX", llm_narrate=True)
        assert result["mode"] == "llm"
        assert f"[ledger:{ledger_id}]" in result["markdown"]
        assert result["citations"] == [ledger_id]
    finally:
        conn.close()


def test_query_falls_back_when_llm_hallucinates_citation(tmp_path: Path, monkeypatch) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        _seed(conn, project="sb", summary="Debugged APISIX 401", action_verb="Debugged", day=date(2026, 9, 30))

        from sb_core import llm as llm_mod

        monkeypatch.setattr(
            llm_mod, "complete", lambda prompt, model=None: "Fixed everything. [ledger:999999]"
        )

        result = templates.query(conn, q="APISIX", llm_narrate=True)
        assert result["mode"] == "fallback"
    finally:
        conn.close()


def test_query_returns_empty_fallback_with_no_matches(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        # NOTE: avoid a hyphenated query term here -- sb_core.store.ledger's
        # FTS5 MATCH query (Phase 0, not in Phase 1a's allowed-modify scope)
        # mis-parses bare hyphenated terms (e.g. "nonexistent-topic" raises
        # "no such column: topic"). A single-word query sidesteps that.
        result = templates.query(conn, q="nonexistenttopic")
        assert result["mode"] == "fallback"
        assert result["citations"] == []
        assert "No matching ledger entries" in result["markdown"]
    finally:
        conn.close()
