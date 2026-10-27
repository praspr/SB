"""Tests for the normalized sb_ledger_refs index (M2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sb_core.store.db import connect
from sb_core.store.ledger import append_ledger, by_ref


def _count_refs(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM sb_ledger_refs").fetchone()[0]


def test_insert_populates_ledger_refs_index(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        append_ledger(
            conn,
            project="sb",
            summary="Debugged CXP-1 and CXP-2",
            action_verb="Debugged",
            refs=[
                {"kind": "jira", "value": "CXP-1"},
                {"kind": "jira", "value": "CXP-2"},
                {"kind": "todo", "value": 42},
            ],
        )
        assert _count_refs(conn) == 3
        rows = conn.execute(
            "SELECT kind, value FROM sb_ledger_refs ORDER BY kind, value"
        ).fetchall()
        assert (rows[0]["kind"], rows[0]["value"]) == ("jira", "CXP-1")
        assert ("todo", "42") in [(r["kind"], r["value"]) for r in rows]
    finally:
        conn.close()


def test_by_ref_uses_index_and_matches(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        append_ledger(
            conn, project="sb", summary="first", refs=[{"kind": "jira", "value": "CXP-9"}]
        )
        append_ledger(
            conn, project="sb", summary="second", refs=[{"kind": "jira", "value": "CXP-9"}]
        )
        append_ledger(
            conn, project="sb", summary="other", refs=[{"kind": "jira", "value": "CXP-10"}]
        )
        matched = by_ref(conn, kind="jira", value="CXP-9")
        assert {row["summary"] for row in matched} == {"first", "second"}
    finally:
        conn.close()


def test_by_ref_equivalence_with_legacy_scan(tmp_path: Path) -> None:
    from sb_core.store.ledger import _by_ref_scan

    conn = connect(tmp_path / "core.db")
    try:
        for i in range(5):
            append_ledger(
                conn,
                project="sb",
                summary=f"entry {i}",
                refs=[{"kind": "jira", "value": "CXP-1"}] if i % 2 == 0 else [],
            )
        indexed = by_ref(conn, kind="jira", value="CXP-1")
        legacy = _by_ref_scan(conn, kind="jira", value="CXP-1")
        assert {r["id"] for r in indexed} == {r["id"] for r in legacy}
    finally:
        conn.close()


def test_migration_backfills_existing_rows(tmp_path: Path) -> None:
    """Simulate a pre-m12 DB with ledger rows but no refs table, then migrate."""
    import sb_core.store.db as db

    db_path = tmp_path / "core.db"
    conn = connect(db_path)
    try:
        append_ledger(
            conn, project="sb", summary="pre-existing", refs=[{"kind": "jira", "value": "CXP-5"}]
        )
        # Drop the refs table to simulate an older schema, and roll the recorded
        # migration version back below 12.
        conn.execute("DROP TABLE sb_ledger_refs")
        conn.execute("DELETE FROM core_schema_migrations WHERE version >= 12")
        conn.commit()
    finally:
        conn.close()

    # Reconnect with a forced migration run: _m12 should rebuild + backfill.
    conn2 = connect(db_path, force_migrations=True)
    try:
        assert _count_refs(conn2) == 1
        matched = by_ref(conn2, kind="jira", value="CXP-5")
        assert len(matched) == 1
        assert matched[0]["summary"] == "pre-existing"
    finally:
        conn2.close()


def test_append_only_still_enforced_with_refs_index(tmp_path: Path) -> None:
    import sqlite3

    conn = connect(tmp_path / "core.db")
    try:
        result = append_ledger(conn, project="sb", summary="immutable row")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE sb_ledger SET summary = 'tampered' WHERE id = ?", (result["id"],)
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM sb_ledger WHERE id = ?", (result["id"],))
    finally:
        conn.close()
