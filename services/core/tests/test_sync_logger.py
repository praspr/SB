"""Tests for sync_logger.py: advisory lock + best-effort ledger logging
for sync operations (phase 2j)."""

from __future__ import annotations

import fcntl
from datetime import datetime, timezone
from pathlib import Path

import pytest

import sb_core.ledger_tools as lt
import sb_core.sync_logger as sync_logger
from sb_core.store.db import connect
from sb_core.store.ledger import search_ledger


def _patch_conn(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    monkeypatch.setattr(lt, "_get_conn", lambda: connect(db_path))


@pytest.fixture(autouse=True)
def _isolate_lock_dir(tmp_path, monkeypatch):
    """Never touch the real ~/.local/share/sb/sync-locks/ from tests."""
    monkeypatch.setattr(sync_logger, "LOCK_DIR", tmp_path / "sync-locks")


# ---------------------------------------------------------------------------
# sync_lock
# ---------------------------------------------------------------------------


def test_sync_lock_acquires_when_free() -> None:
    with sync_logger.sync_lock("test-adapter") as acquired:
        assert acquired is True


def test_sync_lock_second_concurrent_call_is_not_acquired() -> None:
    path = sync_logger.LOCK_DIR / "test-adapter.lock"
    sync_logger.LOCK_DIR.mkdir(parents=True, exist_ok=True)
    # Hold the lock manually, simulating a concurrent in-flight sync.
    holder = open(path, "w")
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with sync_logger.sync_lock("test-adapter") as acquired:
            assert acquired is False
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
        holder.close()


def test_sync_lock_released_after_context_exits() -> None:
    with sync_logger.sync_lock("release-check") as acquired:
        assert acquired is True
    # A fresh attempt must succeed once the first context has exited.
    with sync_logger.sync_lock("release-check") as acquired2:
        assert acquired2 is True


def test_sync_lock_creates_lock_dir() -> None:
    assert not sync_logger.LOCK_DIR.exists()
    with sync_logger.sync_lock("mkdir-check"):
        pass
    assert sync_logger.LOCK_DIR.exists()


# ---------------------------------------------------------------------------
# record_sync
# ---------------------------------------------------------------------------


def test_record_sync_writes_ledger_row_with_expected_shape(tmp_path, monkeypatch):
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    sync_logger.record_sync("webex", {"meetings": 2, "spaces": 1, "messages": 0})

    conn = connect(db_path)
    try:
        entries = search_ledger(conn, project="sb", verb="Synced")
    finally:
        conn.close()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["action_verb"] == "Synced"
    assert entry["summary"] == "Synced webex: meetings=2, spaces=1, messages=0"
    assert "adapter: webex" in entry["body"]
    assert any(r.get("kind") == "sync" and r.get("value") == "webex" for r in entry["refs"])


def test_record_sync_terse_summary_when_no_changes(tmp_path, monkeypatch):
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    sync_logger.record_sync("jira", {"updated_count": 0, "added_count": 0, "unchanged_count": 0})

    conn = connect(db_path)
    try:
        entries = search_ledger(conn, project="sb", verb="Synced")
    finally:
        conn.close()
    assert len(entries) == 1
    assert entries[0]["summary"] == "Synced jira (no changes)"


def test_record_sync_includes_errors_in_body(tmp_path, monkeypatch):
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    sync_logger.record_sync("jira", {"added_count": 0}, errors=["boom", "also boom"])

    conn = connect(db_path)
    try:
        entries = search_ledger(conn, project="sb", verb="Synced")
    finally:
        conn.close()
    assert "errors: boom; also boom" in entries[0]["body"]


def test_record_sync_dedupes_within_same_minute(tmp_path, monkeypatch):
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    fixed_minute = datetime(2026, 10, 1, 12, 30, 5, tzinfo=timezone.utc)
    sync_logger.record_sync("jira", {"added_count": 0}, now=fixed_minute)
    # Same minute, different second -- must dedupe to the same row.
    sync_logger.record_sync(
        "jira", {"added_count": 0}, now=fixed_minute.replace(second=45)
    )

    conn = connect(db_path)
    try:
        entries = search_ledger(conn, project="sb", verb="Synced")
    finally:
        conn.close()
    assert len(entries) == 1


def test_record_sync_distinct_rows_across_minute_boundary(tmp_path, monkeypatch):
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    minute_one = datetime(2026, 10, 1, 12, 30, 0, tzinfo=timezone.utc)
    minute_two = datetime(2026, 10, 1, 12, 31, 0, tzinfo=timezone.utc)
    sync_logger.record_sync("jira", {"added_count": 0}, now=minute_one)
    sync_logger.record_sync("jira", {"added_count": 0}, now=minute_two)

    conn = connect(db_path)
    try:
        entries = search_ledger(conn, project="sb", verb="Synced")
    finally:
        conn.close()
    assert len(entries) == 2


def test_record_sync_swallows_ledger_log_errors(monkeypatch, caplog):
    def failing_ledger_log(**kwargs):
        raise RuntimeError("db is locked")

    monkeypatch.setattr(lt, "ledger_log", failing_ledger_log)

    with caplog.at_level("WARNING"):
        sync_logger.record_sync("webex", {"meetings": 0})

    assert any("sync_logger.record_sync failed" in rec.message for rec in caplog.records)
