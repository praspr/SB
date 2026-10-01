"""Tests for handled Webex attention state and filters."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import sb_core.triage_tools as tt
import sb_core.webex_handled as wh
from sb_core.store.db import connect
from sb_core.webex_store import list_messages, replace_mirror


def _patch_conn(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    monkeypatch.setattr(wh, "_get_conn", lambda: connect(db_path))
    monkeypatch.setattr(tt, "_get_conn", lambda: connect(db_path))


def _seed_message(conn) -> None:
    replace_mirror(
        conn,
        meetings=[],
        spaces=[{"id": "space-1", "name": "Release room"}],
        messages=[
            {
                "id": "msg-1",
                "space_id": "space-1",
                "space_name": "Release room",
                "sender_name": "Ada",
                "is_mention": True,
                "is_unread": True,
                "preview": "Can you check this?",
                "occurred_at": "2026-09-30T09:00:00Z",
            }
        ],
    )


def test_webex_handled_tools_are_registered_and_mounted() -> None:
    names = {tool.name for tool in asyncio.run(wh.mcp.list_tools())}
    assert {"webex_mark_handled", "webex_mark_unhandled"} <= names

    from sb_core.mcp_app import mcp as parent

    mounted = {tool.name for tool in asyncio.run(parent.list_tools())}
    assert "webex_mark_handled" in mounted
    assert "webex_mark_unhandled" in mounted


def test_mark_and_unmark_message_handled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    conn = connect(db_path)
    try:
        _seed_message(conn)
    finally:
        conn.close()

    result = wh.webex_mark_handled("msg-1", "ignored")
    assert result == {"ok": True, "message_id": "msg-1", "action": "ignored"}

    conn = connect(db_path)
    try:
        row = list_messages(conn)[0]
    finally:
        conn.close()
    assert row["handled_action"] == "ignored"
    assert row["handled_at"] is not None

    undo = wh.webex_mark_unhandled("msg-1")
    assert undo == {"ok": True, "message_id": "msg-1"}

    conn = connect(db_path)
    try:
        row = list_messages(conn)[0]
    finally:
        conn.close()
    assert row["handled_action"] is None
    assert row["handled_at"] is None


def test_replace_mirror_preserves_handled_state(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        _seed_message(conn)
        wh.webex_store.set_message_handled(conn, "msg-1", "completed")
        replace_mirror(
            conn,
            meetings=[],
            spaces=[{"id": "space-1", "name": "Release room"}],
            messages=[
                {
                    "id": "msg-1",
                    "space_id": "space-1",
                    "space_name": "Release room",
                    "sender_name": "Ada Lovelace",
                    "is_mention": True,
                    "is_unread": True,
                    "preview": "Updated preview",
                    "occurred_at": "2026-09-30T09:05:00Z",
                }
            ],
        )
        row = list_messages(conn)[0]
    finally:
        conn.close()

    assert row["preview"] == "Updated preview"
    assert row["handled_action"] == "completed"
    assert row["handled_at"] is not None


def test_attention_filters_hide_handled_unless_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    conn = connect(db_path)
    try:
        replace_mirror(
            conn,
            meetings=[],
            spaces=[
                {"id": "space-1", "name": "Active room"},
                {"id": "space-2", "name": "Muted room"},
            ],
            messages=[
                {
                    "id": "msg-1",
                    "space_id": "space-1",
                    "space_name": "Active room",
                    "sender_name": "Ada",
                    "is_mention": True,
                    "is_unread": True,
                    "preview": "Check this",
                    "occurred_at": "2026-09-30T09:00:00Z",
                },
                {
                    "id": "msg-2",
                    "space_id": "space-2",
                    "space_name": "Muted room",
                    "sender_name": "Bo",
                    "is_mention": True,
                    "is_unread": True,
                    "preview": "Muted but handled",
                    "occurred_at": "2026-09-30T09:05:00Z",
                },
            ],
        )
        conn.execute("UPDATE sb_webex_spaces SET muted = 1 WHERE id = ?", ("space-2",))
        conn.commit()
    finally:
        conn.close()

    wh.webex_mark_handled("msg-1", "completed")

    ranked = tt.webex_attention_ranked()
    assert [row["id"] for row in ranked] == ["msg-2"]

    ranked_with_handled = tt.webex_attention_ranked(include_handled=True)
    assert {row["id"] for row in ranked_with_handled} == {"msg-1", "msg-2"}

    filtered = tt.webex_attention_filtered()
    assert filtered == []

    filtered_with_handled = tt.webex_attention_filtered(include_handled=True)
    assert [row["id"] for row in filtered_with_handled] == ["msg-1"]


def test_mark_handled_rejects_unknown_action(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    with pytest.raises(ValueError, match="action must be one of"):
        wh.webex_mark_handled("msg-1", "later")
