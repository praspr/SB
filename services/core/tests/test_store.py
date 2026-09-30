"""Tests for core SQLite store: migrations, upsert/idempotency, search filters."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sb_core.store.db import connect, run_migrations
from sb_core.store.models import Signal
from sb_core.store.signals import search_signals, upsert_signal

# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


def test_migrations_create_all_required_tables(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "sb_signals" in tables
    assert "sb_sync_state" in tables


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    """Running migrations twice must not raise or double-insert version rows."""
    conn = connect(tmp_path / "core.db")
    run_migrations(conn)  # second run
    versions = conn.execute("SELECT version FROM core_schema_migrations").fetchall()
    version_numbers = [r[0] for r in versions]
    # No duplicates
    assert len(version_numbers) == len(set(version_numbers))


def test_wal_and_foreign_keys_are_enabled(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert mode == "wal"
    assert fk == 1


# ---------------------------------------------------------------------------
# Upsert / idempotency tests
# ---------------------------------------------------------------------------


def test_upsert_inserts_new_signal(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    sig = upsert_signal(
        conn,
        source="test",
        source_id="1",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="Hello",
    )
    assert isinstance(sig, Signal)
    assert sig.id > 0
    assert sig.source == "test"
    assert sig.source_id == "1"
    assert sig.title == "Hello"
    assert sig.kind == "task"


def test_upsert_is_idempotent_on_source_source_id(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    s1 = upsert_signal(
        conn,
        source="test",
        source_id="x",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="Original",
    )
    s2 = upsert_signal(
        conn,
        source="test",
        source_id="x",
        kind="task",
        occurred_at="2026-01-02T00:00:00Z",
        title="Updated",
    )
    # Same row – same id
    assert s1.id == s2.id
    # Latest values
    assert s2.title == "Updated"
    assert s2.occurred_at == "2026-01-02T00:00:00Z"


def test_upsert_stores_optional_fields(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    sig = upsert_signal(
        conn,
        source="git",
        source_id="abc123",
        kind="commit",
        occurred_at="2026-06-01T12:00:00Z",
        title="feat: add feature",
        body="Long description here",
        scope="myrepo",
        verb="committed",
        refs=["https://github.com/x/y/commit/abc123"],
        raw_ref="/repo:abc123",
    )
    assert sig.body == "Long description here"
    assert sig.scope == "myrepo"
    assert sig.verb == "committed"
    assert sig.refs == ["https://github.com/x/y/commit/abc123"]
    assert sig.raw_ref == "/repo:abc123"


def test_upsert_with_empty_refs_defaults_to_empty_list(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    sig = upsert_signal(
        conn,
        source="t",
        source_id="no-refs",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="No refs",
    )
    assert sig.refs == []


# ---------------------------------------------------------------------------
# Search filter tests
# ---------------------------------------------------------------------------


def test_search_by_q_matches_title(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="Deploy feature X",
    )
    upsert_signal(
        conn,
        source="t",
        source_id="2",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="Fix bug Y",
    )
    results = search_signals(conn, q="feature")
    assert len(results) == 1
    assert results[0].title == "Deploy feature X"


def test_search_by_q_matches_body(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="3",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="A task",
        body="contains the needle",
    )
    results = search_signals(conn, q="needle")
    assert len(results) == 1
    assert results[0].source_id == "3"


def test_search_by_source_filter(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="todos",
        source_id="1",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="A",
    )
    upsert_signal(
        conn,
        source="jira",
        source_id="J1",
        kind="ticket",
        occurred_at="2026-01-01T00:00:00Z",
        title="B",
    )
    results = search_signals(conn, source="jira")
    assert len(results) == 1
    assert results[0].source == "jira"


def test_search_by_kind_filter(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="A",
    )
    upsert_signal(
        conn,
        source="t",
        source_id="2",
        kind="commit",
        occurred_at="2026-01-01T00:00:00Z",
        title="B",
    )
    results = search_signals(conn, kind="commit")
    assert len(results) == 1
    assert results[0].kind == "commit"


def test_search_by_since_filter(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="old",
        kind="task",
        occurred_at="2025-01-01T00:00:00Z",
        title="Old",
    )
    upsert_signal(
        conn,
        source="t",
        source_id="new",
        kind="task",
        occurred_at="2026-06-01T00:00:00Z",
        title="New",
    )
    results = search_signals(conn, since="2026-01-01T00:00:00Z")
    assert len(results) == 1
    assert results[0].title == "New"


def test_search_results_include_id_for_citations(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="cite1",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="Cited result",
    )
    results = search_signals(conn)
    assert all(r.id > 0 for r in results)


def test_search_respects_limit(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    for i in range(10):
        upsert_signal(
            conn,
            source="t",
            source_id=str(i),
            kind="task",
            occurred_at="2026-01-01T00:00:00Z",
            title=f"T{i}",
        )
    results = search_signals(conn, limit=3)
    assert len(results) == 3


def test_search_no_filters_returns_all_up_to_limit(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    for i in range(5):
        upsert_signal(
            conn,
            source="t",
            source_id=str(i),
            kind="task",
            occurred_at="2026-01-01T00:00:00Z",
            title=f"T{i}",
        )
    results = search_signals(conn)
    assert len(results) == 5


def test_search_combined_filters(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="jira",
        source_id="J1",
        kind="ticket",
        occurred_at="2026-06-01T00:00:00Z",
        title="Deploy jira item",
    )
    upsert_signal(
        conn,
        source="todos",
        source_id="T1",
        kind="task",
        occurred_at="2026-06-01T00:00:00Z",
        title="Deploy todo item",
    )
    results = search_signals(conn, q="Deploy", source="jira")
    assert len(results) == 1
    assert results[0].source == "jira"


# ---------------------------------------------------------------------------
# Issue 5: LIKE escape for %, _, backslash
# ---------------------------------------------------------------------------


def test_like_search_percent_is_treated_as_literal(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="100% done",
    )
    upsert_signal(
        conn,
        source="t",
        source_id="2",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="almost done",
    )
    # Searching for literal "%" should only match the first signal, not everything
    results = search_signals(conn, q="%")
    assert len(results) == 1
    assert results[0].title == "100% done"


def test_like_search_underscore_is_treated_as_literal(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="my_variable",
    )
    upsert_signal(
        conn,
        source="t",
        source_id="2",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="myvariable",
    )
    # "_" as literal should only match "my_variable", not act as single-char wildcard
    results = search_signals(conn, q="my_variable")
    assert len(results) == 1
    assert results[0].title == "my_variable"


def test_like_search_backslash_is_treated_as_literal(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title=r"path\to\file",
    )
    upsert_signal(
        conn,
        source="t",
        source_id="2",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="other task",
    )
    results = search_signals(conn, q=r"path\to")
    assert len(results) == 1
    assert r"path\to\file" in results[0].title


# ---------------------------------------------------------------------------
# Issue 3: occurred_at normalization
# ---------------------------------------------------------------------------


def test_occurred_at_normalized_from_space_format(tmp_path: Path) -> None:
    """Space-separated datetime stored as canonical YYYY-MM-DDTHH:MM:SSZ."""
    conn = connect(tmp_path / "core.db")
    sig = upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-06-15 14:30:00",
        title="Space format",
    )
    assert sig.occurred_at == "2026-06-15T14:30:00Z"


def test_occurred_at_normalized_from_iso_offset(tmp_path: Path) -> None:
    """ISO datetime with +05:30 offset stored as UTC."""
    conn = connect(tmp_path / "core.db")
    sig = upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-06-15T14:30:00+05:30",
        title="Offset format",
    )
    # 14:30 +05:30 = 09:00 UTC
    assert sig.occurred_at == "2026-06-15T09:00:00Z"


def test_occurred_at_normalized_from_date_only(tmp_path: Path) -> None:
    """Date-only string stored as T00:00:00Z."""
    conn = connect(tmp_path / "core.db")
    sig = upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-01-15",
        title="Date only",
    )
    assert sig.occurred_at == "2026-01-15T00:00:00Z"


def test_occurred_at_canonical_passthrough(tmp_path: Path) -> None:
    """Already-canonical YYYY-MM-DDTHH:MM:SSZ passes through unchanged."""
    conn = connect(tmp_path / "core.db")
    sig = upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-03-21T12:00:00Z",
        title="Canonical",
    )
    assert sig.occurred_at == "2026-03-21T12:00:00Z"


def test_since_filter_works_at_exact_boundary(tmp_path: Path) -> None:
    """since= is an inclusive lower bound; same-second equality must work."""
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="1",
        kind="task",
        occurred_at="2026-06-01T00:00:00Z",
        title="Exactly at boundary",
    )
    upsert_signal(
        conn,
        source="t",
        source_id="2",
        kind="task",
        occurred_at="2026-05-31T23:59:59Z",
        title="One second before",
    )
    results = search_signals(conn, since="2026-06-01T00:00:00Z")
    assert len(results) == 1
    assert results[0].title == "Exactly at boundary"


def test_signals_ordered_correctly_across_normalised_formats(tmp_path: Path) -> None:
    """Signals inserted with varied input formats must order correctly after normalisation."""
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="early",
        kind="task",
        occurred_at="2026-01-01 08:00:00",
        title="Earlier",
    )
    upsert_signal(
        conn,
        source="t",
        source_id="late",
        kind="task",
        occurred_at="2026-12-31T23:59:59Z",
        title="Later",
    )
    results = search_signals(conn)
    assert results[0].title == "Later"  # most-recent first
    assert results[1].title == "Earlier"


# ---------------------------------------------------------------------------
# Issue 6: canonical UTC in created_at / sync state timestamps
# ---------------------------------------------------------------------------


def test_upsert_created_at_is_iso_utc(tmp_path: Path) -> None:
    """created_at must be canonical ISO UTC: YYYY-MM-DDTHH:MM:SSZ."""
    conn = connect(tmp_path / "core.db")
    sig = upsert_signal(
        conn,
        source="t",
        source_id="ts",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="Timestamp test",
    )
    assert "T" in sig.created_at
    assert sig.created_at.endswith("Z")
    # Must be parseable
    from datetime import datetime, timezone

    dt = datetime.strptime(sig.created_at, "%Y-%m-%dT%H:%M:%SZ")
    assert dt is not None


# ---------------------------------------------------------------------------
# Issue 1: fresh connections — concurrent safety
# ---------------------------------------------------------------------------


def test_concurrent_fresh_connections_no_errors(tmp_path: Path) -> None:
    """Concurrent upserts and searches using independent fresh connections must not error."""
    import threading

    db_path = tmp_path / "core.db"
    # Initialise schema first
    init_conn = connect(db_path)
    init_conn.close()

    errors: list[Exception] = []

    def writer(n: int) -> None:
        for i in range(10):
            c = connect(db_path)
            try:
                upsert_signal(
                    c,
                    source="concurrent",
                    source_id=f"{n}-{i}",
                    kind="task",
                    occurred_at="2026-01-01T00:00:00Z",
                    title=f"Signal {n}-{i}",
                )
            except Exception as exc:
                errors.append(exc)
            finally:
                c.close()

    def reader() -> None:
        for _ in range(10):
            c = connect(db_path)
            try:
                search_signals(c, source="concurrent")
            except Exception as exc:
                errors.append(exc)
            finally:
                c.close()

    threads = [
        threading.Thread(target=writer, args=(0,)),
        threading.Thread(target=writer, args=(1,)),
        threading.Thread(target=reader),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"Concurrent errors: {errors}"
