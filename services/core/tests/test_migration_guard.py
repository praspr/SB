"""Tests for the per-process migration guard (M1) in sb_core.store.db."""

from __future__ import annotations

from pathlib import Path

import sb_core.store.db as db
from sb_core.store.db import connect, reset_migration_guard, schema_version


def test_first_connect_fully_migrates(tmp_path: Path) -> None:
    reset_migration_guard()
    path = tmp_path / "core.db"
    conn = connect(path)
    try:
        assert schema_version(conn) == len(db._MIGRATIONS)
    finally:
        conn.close()


def test_second_connect_skips_migration_run(tmp_path: Path, monkeypatch) -> None:
    reset_migration_guard()
    path = tmp_path / "core.db"

    calls = {"n": 0}
    real_run = db.run_migrations

    def _counting_run(conn):
        calls["n"] += 1
        return real_run(conn)

    monkeypatch.setattr(db, "run_migrations", _counting_run)

    connect(path).close()
    connect(path).close()
    connect(path).close()
    # Migrations run exactly once for the same path within a process.
    assert calls["n"] == 1


def test_force_migrations_reruns(tmp_path: Path, monkeypatch) -> None:
    reset_migration_guard()
    path = tmp_path / "core.db"

    calls = {"n": 0}
    real_run = db.run_migrations

    def _counting_run(conn):
        calls["n"] += 1
        return real_run(conn)

    monkeypatch.setattr(db, "run_migrations", _counting_run)

    connect(path).close()
    connect(path, force_migrations=True).close()
    assert calls["n"] == 2


def test_distinct_paths_each_migrate(tmp_path: Path, monkeypatch) -> None:
    reset_migration_guard()
    calls = {"n": 0}
    real_run = db.run_migrations

    def _counting_run(conn):
        calls["n"] += 1
        return real_run(conn)

    monkeypatch.setattr(db, "run_migrations", _counting_run)

    connect(tmp_path / "a.db").close()
    connect(tmp_path / "b.db").close()
    assert calls["n"] == 2


def test_fresh_db_after_guard_reset_still_migrates(tmp_path: Path) -> None:
    reset_migration_guard()
    path = tmp_path / "core.db"
    connect(path).close()
    # Simulate a new process: clear the guard, delete the DB, reconnect.
    reset_migration_guard()
    path.unlink()
    conn = connect(path)
    try:
        assert schema_version(conn) == len(db._MIGRATIONS)
    finally:
        conn.close()
