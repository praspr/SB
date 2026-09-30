"""Tests for migration _m10_webex_threads: parent-message metadata columns
and the cached Webex identity table."""

from __future__ import annotations

from pathlib import Path

from sb_core.store.db import connect


def test_m10_adds_parent_columns_to_webex_messages(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(sb_webex_messages)").fetchall()
        }
        assert "parent_message_id" in columns
        assert "parent_sender_email" in columns
        assert "is_reply_to_me" in columns
    finally:
        conn.close()


def test_new_message_row_can_carry_the_three_new_fields(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        conn.execute(
            """
            INSERT INTO sb_webex_messages
              (id, space_id, space_name, sender_name, is_dm, is_mention, is_unread,
               preview, occurred_at, synced_at, parent_message_id,
               parent_sender_email, is_reply_to_me)
            VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?, ?, ?, ?, ?)
            """,
            (
                "msg-1",
                "space-1",
                "Team room",
                "Ada",
                "Sure thing",
                "2026-09-30T09:00:00Z",
                "2026-09-30T09:00:00Z",
                "parent-msg-1",
                "me@example.com",
                1,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sb_webex_messages WHERE id = ?", ("msg-1",)
        ).fetchone()
        assert row["parent_message_id"] == "parent-msg-1"
        assert row["parent_sender_email"] == "me@example.com"
        assert row["is_reply_to_me"] == 1
    finally:
        conn.close()


def test_default_is_reply_to_me_is_zero_and_parent_fields_are_null(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        conn.execute(
            """
            INSERT INTO sb_webex_messages
              (id, space_id, space_name, sender_name, is_dm, is_mention, is_unread,
               preview, occurred_at, synced_at)
            VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?, ?)
            """,
            ("msg-2", "space-1", "Team room", "Bo", "hi", "2026-09-30T09:00:00Z", "2026-09-30T09:00:00Z"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sb_webex_messages WHERE id = ?", ("msg-2",)
        ).fetchone()
        assert row["parent_message_id"] is None
        assert row["parent_sender_email"] is None
        assert row["is_reply_to_me"] == 0
    finally:
        conn.close()


def test_m10_creates_webex_identity_table(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        conn.execute(
            "INSERT INTO sb_webex_identity (email, display_name, cached_at) VALUES (?, ?, ?)",
            ("me@example.com", "Me Myself", "2026-09-30T09:00:00Z"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sb_webex_identity WHERE email = ?", ("me@example.com",)
        ).fetchone()
        assert row["display_name"] == "Me Myself"
    finally:
        conn.close()


def test_migration_is_idempotent_on_second_connect(tmp_path: Path) -> None:
    db_path = tmp_path / "core.db"
    conn1 = connect(db_path)
    conn1.close()
    conn2 = connect(db_path)
    try:
        columns = {
            row[1]
            for row in conn2.execute("PRAGMA table_info(sb_webex_messages)").fetchall()
        }
        assert "is_reply_to_me" in columns
    finally:
        conn2.close()
