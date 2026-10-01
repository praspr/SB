"""End-to-end verification (phase 2j): sync operations log to the ledger
with a minute-bucketed dedupe hash, and the advisory flock prevents
concurrent fires of the same adapter from double-logging.

Note: in production, ``sb_project_registry`` already has a row for
project="sb" because ``seed_registry_if_empty`` (see ``sb_core.config``)
seeds it on first boot. Here we register it explicitly with
``sync_mode='sqlite-only'`` since this test only cares about the ledger
row, not CHANGELOG.md dual-sync.
"""

from __future__ import annotations

import fcntl
from datetime import datetime, timezone
from pathlib import Path

import pytest

import sb_core.ledger_tools as lt
import sb_core.sync_logger as sync_logger
import sb_core.sync_tools as st
from sb_core.adapters import AdapterResult
from sb_core.store.db import connect
from sb_core.store.ledger import register_project, search_ledger


@pytest.fixture(autouse=True)
def _isolate_lock_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_logger, "LOCK_DIR", tmp_path / "sync-locks")


@pytest.fixture
def core_db_path(tmp_path: Path) -> Path:
    return tmp_path / "core.db"


@pytest.fixture(autouse=True)
def _patch_conn_and_enroll(tmp_path, core_db_path, monkeypatch):
    monkeypatch.setattr(st, "_get_conn", lambda: connect(core_db_path))
    monkeypatch.setattr(lt, "_get_conn", lambda: connect(core_db_path))
    # See module docstring: production seeds this row automatically via
    # seed_registry_if_empty; we seed it explicitly here for test isolation.
    conn = connect(core_db_path)
    try:
        register_project(
            conn,
            project="sb",
            root_path=str(tmp_path),
            sync_mode="sqlite-only",
        )
    finally:
        conn.close()


def _fake_adapter_result(name, db_path, config):
    return AdapterResult(adapter=name, signal_count=0, error=None)


def test_sync_adapters_logs_one_ledger_row_per_run(
    core_db_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(st, "_run_one_adapter", _fake_adapter_result)

    fixed_minute = datetime(2026, 10, 1, 12, 30, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(st, "record_sync", _bind_now(fixed_minute))

    st.sync_adapters(adapters=["changelog"])

    conn = connect(core_db_path)
    try:
        entries = search_ledger(conn, project="sb", verb="Synced")
    finally:
        conn.close()
    assert len(entries) == 1


def _bind_now(now):
    def _wrapped(adapter, counts, errors=None):
        return sync_logger.record_sync(adapter, counts, errors, now=now)

    return _wrapped


def test_sync_adapters_same_second_rerun_dedupes(core_db_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(st, "_run_one_adapter", _fake_adapter_result)

    fixed_minute = datetime(2026, 10, 1, 12, 30, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(st, "record_sync", _bind_now(fixed_minute))

    st.sync_adapters(adapters=["changelog"])
    st.sync_adapters(adapters=["changelog"])  # same injected minute -> dedup

    conn = connect(core_db_path)
    try:
        entries = search_ledger(conn, project="sb", verb="Synced")
    finally:
        conn.close()
    assert len(entries) == 1


def test_sync_adapters_next_minute_adds_second_row(core_db_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(st, "_run_one_adapter", _fake_adapter_result)

    minute_one = datetime(2026, 10, 1, 12, 30, 0, tzinfo=timezone.utc)
    minute_two = datetime(2026, 10, 1, 12, 31, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(st, "record_sync", _bind_now(minute_one))
    st.sync_adapters(adapters=["changelog"])

    monkeypatch.setattr(st, "record_sync", _bind_now(minute_two))
    st.sync_adapters(adapters=["changelog"])

    conn = connect(core_db_path)
    try:
        entries = search_ledger(conn, project="sb", verb="Synced")
    finally:
        conn.close()
    assert len(entries) == 2


def test_concurrent_sync_adapters_returns_already_running_and_does_not_log(
    core_db_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(st, "_run_one_adapter", _fake_adapter_result)

    # Simulate a concurrent in-flight sync by holding the lock manually.
    sync_logger.LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = sync_logger.LOCK_DIR / "adapters.lock"
    holder = open(lock_path, "w")
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        result = st.sync_adapters(adapters=["changelog"])
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
        holder.close()

    assert result == {"status": "already_running", "adapters": {}}

    conn = connect(core_db_path)
    try:
        entries = search_ledger(conn, project="sb")
    finally:
        conn.close()
    assert entries == []
