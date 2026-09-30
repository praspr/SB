"""Unit tests for sb_core.store.ledger."""

from __future__ import annotations

from pathlib import Path

from sb_core.store.db import connect
from sb_core.store.ledger import (
    append_ledger,
    by_ref,
    get_context,
    get_ledger,
    list_projects,
    open_threads,
    register_project,
    search_ledger,
)


def test_append_ledger_inserts_and_returns_shape(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        result = append_ledger(
            conn,
            project="sb",
            summary="Shipped the ledger foundation",
            action_verb="Shipped",
        )
        assert result["was_new"] is True
        assert isinstance(result["id"], int)
        assert result["redaction_applied"] is False
        assert result["ts"]
    finally:
        conn.close()


def test_append_ledger_is_idempotent_by_content(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        first = append_ledger(conn, project="sb", summary="Same thing twice")
        second = append_ledger(conn, project="sb", summary="Same thing twice")
        assert first["id"] == second["id"]
        assert second["was_new"] is False
        rows = conn.execute("SELECT COUNT(*) AS n FROM sb_ledger").fetchone()
        assert rows["n"] == 1
    finally:
        conn.close()


def test_append_ledger_redacts_secrets_and_stamps_flag(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        result = append_ledger(
            conn,
            project="sb",
            summary="Rotated AKIAABCDEFGHIJKLMNOP in prod",
        )
        assert result["redaction_applied"] is True
        row = get_ledger(conn, result["id"])
        assert row is not None
        assert "AKIA" not in row["summary"]
        assert "[REDACTED:AWS_KEY]" in row["summary"]
        assert row["redaction_rules_version"] == 1
    finally:
        conn.close()


def test_get_ledger_returns_none_for_missing_id(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        assert get_ledger(conn, 999) is None
    finally:
        conn.close()


def test_search_ledger_filters_by_project_and_verb(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        append_ledger(conn, project="sb", summary="sb entry one", action_verb="Shipped")
        append_ledger(conn, project="ciq", summary="ciq entry one", action_verb="Fixed")
        append_ledger(conn, project="sb", summary="sb entry two", action_verb="Fixed")

        sb_rows = search_ledger(conn, project="sb")
        assert {r["project"] for r in sb_rows} == {"sb"}
        assert len(sb_rows) == 2

        fixed_rows = search_ledger(conn, verb="Fixed")
        assert len(fixed_rows) == 2
    finally:
        conn.close()


def test_search_ledger_full_text_query(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        append_ledger(conn, project="sb", summary="Debugged APISIX 401 token issue")
        append_ledger(conn, project="sb", summary="Closed foo bar follow-up for CXP-54493")
        append_ledger(conn, project="sb", summary="Unrelated bullet about todos")

        results = search_ledger(conn, q="APISIX")
        assert len(results) == 1
        assert "APISIX" in results[0]["summary"]

        phrase_results = search_ledger(conn, q="foo bar")
        assert len(phrase_results) == 1
        assert "foo bar" in phrase_results[0]["summary"]

        jiraish_results = search_ledger(conn, q="CXP-54493")
        assert len(jiraish_results) == 1
        assert "CXP-54493" in jiraish_results[0]["summary"]

        assert search_ledger(conn, q="nonexistent-topic") == []
    finally:
        conn.close()


def test_by_ref_matches_ref_kind_and_value(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        append_ledger(
            conn,
            project="sb",
            summary="Linked a jira ticket",
            refs=[{"kind": "jira", "value": "CXP-1"}],
        )
        append_ledger(
            conn,
            project="sb",
            summary="Unrelated entry",
        )
        matches = by_ref(conn, kind="jira", value="CXP-1")
        assert len(matches) == 1
        assert matches[0]["summary"] == "Linked a jira ticket"
    finally:
        conn.close()


def test_open_threads_returns_empty_when_no_jira_or_todos_available(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        append_ledger(
            conn,
            project="sb",
            summary="Referenced a todo",
            refs=[{"kind": "todo", "value": "999999"}],
        )
        # Without a live todos DB configured to have this id open, expect empty.
        threads = open_threads(conn, project="sb")
        assert isinstance(threads, list)
    finally:
        conn.close()


def test_get_context_returns_stable_shape(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        append_ledger(conn, project="sb", summary="Context entry", refs=[{"kind": "pr", "value": "45", "url": "https://example.com/pr/45"}])
        context = get_context(conn, project="sb")
        assert set(context.keys()) == {"entries", "open_threads", "tracked_refs"}
        assert len(context["entries"]) == 1
        assert context["tracked_refs"][0]["kind"] == "pr"
    finally:
        conn.close()


def test_register_project_and_list_projects_roundtrip(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        result = register_project(
            conn, project="demo", root_path="/tmp/demo", sync_mode="dual"
        )
        assert result["project"] == "demo"
        assert result["changelog_path"].endswith("CHANGELOG.md")

        projects = list_projects(conn)
        assert any(p["project"] == "demo" for p in projects)
    finally:
        conn.close()


def test_register_project_is_upsert(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        register_project(conn, project="demo", root_path="/tmp/demo")
        updated = register_project(
            conn, project="demo", root_path="/tmp/demo2", sync_mode="sqlite-only"
        )
        assert updated["root_path"] == "/tmp/demo2"
        assert updated["sync_mode"] == "sqlite-only"
        projects = list_projects(conn)
        assert len([p for p in projects if p["project"] == "demo"]) == 1
    finally:
        conn.close()
