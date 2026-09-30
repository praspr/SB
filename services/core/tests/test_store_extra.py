"""Extra store tests: robust migrations, column-specific daily writes,
proposal state machine, and UTC-range signal search."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from sb_core.store import daily as daily_store
from sb_core.store.db import connect, run_migrations
from sb_core.store.signals import search_signals, upsert_signal

# ---------------------------------------------------------------------------
# Item 5: migrations — atomic, partial-recovery, concurrent bootstrap
# ---------------------------------------------------------------------------


def test_partially_applied_add_column_is_recovered(tmp_path: Path) -> None:
    """A column added but whose version row is missing must not crash a rerun."""
    db = tmp_path / "core.db"
    conn = connect(db)  # fully migrated
    # Simulate a crash between ALTER TABLE and the version INSERT: the column
    # exists but the migration version is not recorded.
    max_version = conn.execute(
        "SELECT MAX(version) FROM core_schema_migrations"
    ).fetchone()[0]
    conn.execute("DELETE FROM core_schema_migrations WHERE version = ?", (max_version,))
    conn.commit()

    # Re-running must not raise "duplicate column name" and must re-record it.
    run_migrations(conn)
    versions = {
        r[0]
        for r in conn.execute("SELECT version FROM core_schema_migrations").fetchall()
    }
    assert max_version in versions
    conn.close()


def test_missing_required_columns_are_added(tmp_path: Path) -> None:
    """If sb_proposals lacks target_path/updated_at, connect() repairs it."""
    db = tmp_path / "core.db"
    raw = sqlite3.connect(str(db))
    raw.execute("""
        CREATE TABLE sb_proposals (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT NOT NULL,
          title TEXT NOT NULL,
          body TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'pending',
          signal_refs TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          decided_at TEXT
        )
        """)
    # Pretend all migrations already ran so the loop would skip the ALTERs.
    raw.execute(
        "CREATE TABLE core_schema_migrations (version INTEGER PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    for v in range(1, 7):
        raw.execute("INSERT INTO core_schema_migrations (version) VALUES (?)", (v,))
    raw.commit()
    raw.close()

    conn = connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sb_proposals)").fetchall()}
    assert "target_path" in cols
    assert "updated_at" in cols
    conn.close()


def test_concurrent_connect_bootstrap_no_errors(tmp_path: Path) -> None:
    db = tmp_path / "core.db"
    errors: list[Exception] = []

    def worker() -> None:
        try:
            c = connect(db)
            c.execute("SELECT 1").fetchone()
            c.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)
    assert not errors, f"Concurrent bootstrap errors: {errors}"


# ---------------------------------------------------------------------------
# Item 6: column-specific daily writes (no lost updates)
# ---------------------------------------------------------------------------


def test_save_plan_then_save_wrap_do_not_clobber(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    daily_store.save_plan(conn, "2026-09-30", "PLAN MD", {"ranked": [1]})
    daily_store.save_wrap(conn, "2026-09-30", "WRAP MD", {"signal_ids": [2]})

    got = daily_store.get_daily(conn, "2026-09-30")
    assert got["plan_md"] == "PLAN MD"
    assert got["plan_data"] == {"ranked": [1]}
    assert got["wrap_md"] == "WRAP MD"
    assert got["wrap_data"] == {"signal_ids": [2]}
    conn.close()


def test_save_wrap_preserves_existing_plan(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    daily_store.save_plan(conn, "2026-09-30", "PLAN", {"a": 1})
    # Writing wrap must not null out plan columns.
    daily_store.save_wrap(conn, "2026-09-30", "WRAP", {"b": 2})
    got = daily_store.get_daily(conn, "2026-09-30")
    assert got["plan_md"] == "PLAN"
    assert got["wrap_md"] == "WRAP"
    conn.close()


def test_persist_wrap_and_proposal_in_one_transaction(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    proposal = daily_store.persist_wrap(
        conn,
        "2026-09-30",
        "WRAP",
        {"signal_ids": [1]},
        proposal={
            "kind": "changelog",
            "title": "t",
            "target_path": str(tmp_path / "CHANGELOG.md"),
            "payload": "## x\n",
            "signal_refs": [1],
        },
    )
    assert proposal is not None
    assert daily_store.get_daily(conn, "2026-09-30")["wrap_md"] == "WRAP"
    pending = daily_store.list_proposals(conn, status="pending")
    assert len(pending) == 1
    conn.close()


def test_find_pending_proposal_dedup(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    target = str(tmp_path / "CHANGELOG.md")
    daily_store.create_proposal(
        conn, kind="changelog", title="t", target_path=target, payload="## x\n"
    )
    found = daily_store.find_pending_proposal(
        conn, target_path=target, payload="## x\n"
    )
    assert found is not None
    missing = daily_store.find_pending_proposal(
        conn, target_path=target, payload="different\n"
    )
    assert missing is None
    conn.close()


# ---------------------------------------------------------------------------
# Item 1: proposal state machine
# ---------------------------------------------------------------------------


def test_transition_only_from_expected_status(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    p = daily_store.create_proposal(
        conn, kind="changelog", title="t", target_path="x", payload="y"
    )
    pid = p["id"]
    # pending -> rejected succeeds
    assert daily_store.transition_proposal(conn, pid, "pending", "rejected") is True
    # rejected -> executed must fail (not from pending)
    assert daily_store.transition_proposal(conn, pid, "pending", "executed") is False
    assert daily_store.get_proposal(conn, pid)["status"] == "rejected"
    conn.close()


# ---------------------------------------------------------------------------
# Item 8: search_signals UTC range (until, exclusive)
# ---------------------------------------------------------------------------


def test_search_signals_until_is_exclusive_upper_bound(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    upsert_signal(
        conn,
        source="t",
        source_id="in",
        kind="task",
        occurred_at="2026-09-29T20:00:00Z",
        title="inside range",
    )
    upsert_signal(
        conn,
        source="t",
        source_id="edge",
        kind="task",
        occurred_at="2026-09-30T18:30:00Z",
        title="at upper bound",
    )
    results = search_signals(
        conn,
        since="2026-09-29T18:30:00Z",
        until="2026-09-30T18:30:00Z",
    )
    titles = {r.title for r in results}
    assert "inside range" in titles
    assert "at upper bound" not in titles  # until is exclusive
    conn.close()
