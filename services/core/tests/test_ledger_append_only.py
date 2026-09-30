"""sb_ledger must never allow UPDATE or DELETE — proposal/correction only."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sb_core.store.db import connect


def _seed_row(conn: sqlite3.Connection) -> int:
    conn.execute(
        """
        INSERT INTO sb_ledger
          (ts, session_id, project, action_verb, summary, refs, source_harness, origin, content_sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "2026-09-30T00:00:00Z",
            "sess-1",
            "sb",
            "Note",
            "seed row",
            "[]",
            "test",
            "test",
            "deadbeef",
        ),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM sb_ledger WHERE content_sha256 = ?", ("deadbeef",)).fetchone()
    return int(row["id"])


def test_migration_creates_ledger_tables(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "sb_ledger" in tables
        assert "sb_ledger_sessions" in tables
        assert "sb_project_registry" in tables
        fts_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            ).fetchall()
        }
        assert "sb_ledger_fts" in fts_tables
    finally:
        conn.close()


def test_update_is_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        _seed_row(conn)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE sb_ledger SET summary = 'edited' WHERE content_sha256 = ?", ("deadbeef",))
            conn.commit()
    finally:
        conn.close()


def test_delete_is_rejected(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        _seed_row(conn)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM sb_ledger WHERE content_sha256 = ?", ("deadbeef",))
            conn.commit()
    finally:
        conn.close()


def test_insert_is_allowed_and_mirrors_to_fts(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        ledger_id = _seed_row(conn)
        fts_row = conn.execute(
            "SELECT rowid FROM sb_ledger_fts WHERE rowid = ?", (ledger_id,)
        ).fetchone()
        assert fts_row is not None
    finally:
        conn.close()


def test_dedup_unique_index_rejects_duplicate_content_sha256(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        _seed_row(conn)
        with pytest.raises(sqlite3.IntegrityError):
            _seed_row(conn)
    finally:
        conn.close()
