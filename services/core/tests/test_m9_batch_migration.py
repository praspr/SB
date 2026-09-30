"""Tests for migration _m9_batch: muted spaces column, scheduled rituals,
and the DB-backed goals registry."""

from __future__ import annotations

from pathlib import Path

from sb_core.store.db import connect


def test_m9_adds_muted_column_to_webex_spaces(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(sb_webex_spaces)").fetchall()
        }
        assert "muted" in columns
        conn.execute(
            "INSERT INTO sb_webex_spaces (id, name, synced_at) VALUES (?, ?, ?)",
            ("space-1", "Space One", "2026-09-30T00:00:00Z"),
        )
        row = conn.execute(
            "SELECT muted FROM sb_webex_spaces WHERE id = ?", ("space-1",)
        ).fetchone()
        assert row["muted"] == 0
    finally:
        conn.close()


def test_m9_creates_scheduled_rituals_table(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        conn.execute(
            """
            INSERT INTO sb_scheduled_rituals (name, ritual, cron)
            VALUES (?, ?, ?)
            """,
            ("Friday wrap", "wrap_day", "0 16 * * 5"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sb_scheduled_rituals WHERE name = ?", ("Friday wrap",)
        ).fetchone()
        assert row["ritual"] == "wrap_day"
        assert row["enabled"] == 1
        assert row["args_json"] == "{}"
    finally:
        conn.close()


def test_m9_creates_goals_registry_table(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        conn.execute(
            """
            INSERT INTO sb_goals_registry (tier, title, keywords)
            VALUES (?, ?, ?)
            """,
            ("quarterly", "Ship the ledger", '["ledger", "phase"]'),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sb_goals_registry WHERE title = ?", ("Ship the ledger",)
        ).fetchone()
        assert row["tier"] == "quarterly"
        assert row["status"] == "active"
    finally:
        conn.close()


def test_migration_is_idempotent_on_second_connect(tmp_path: Path) -> None:
    db_path = tmp_path / "core.db"
    conn1 = connect(db_path)
    conn1.close()
    conn2 = connect(db_path)
    try:
        columns = {
            row[1] for row in conn2.execute("PRAGMA table_info(sb_webex_spaces)").fetchall()
        }
        assert "muted" in columns
    finally:
        conn2.close()
