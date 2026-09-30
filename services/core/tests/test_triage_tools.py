"""Exercise the triage MCP surface with local mirror fixtures only."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import sb_core.triage_tools as tt
from sb_core.store import daily as daily_store
from sb_core.store.db import connect
from sb_core.store.ledger import append_ledger
from sb_core.webex_store import replace_mirror


def _patch_conns(
    monkeypatch: pytest.MonkeyPatch, core_db: Path, todos_db: Path
) -> None:
    from sb_todos.db import connect as connect_todos

    monkeypatch.setattr(tt, "_get_conn", lambda: connect(core_db))
    monkeypatch.setattr(tt, "_get_todos_conn", lambda: connect_todos(todos_db))


def test_triage_tools_are_registered_and_mounted() -> None:
    names = {tool.name for tool in asyncio.run(tt.mcp.list_tools())}
    assert {
        "webex_attention_ranked",
        "webex_attention_filtered",
        "pre_meeting_context",
        "propose_meeting_notes",
    } <= names

    from sb_core.mcp_app import mcp as parent

    mounted = {tool.name for tool in asyncio.run(parent.list_tools())}
    assert "pre_meeting_context" in mounted
    assert "propose_meeting_notes" in mounted
    assert "webex_attention_filtered" in mounted


def test_webex_attention_ranked_adds_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    core_db = tmp_path / "core.db"
    todos_db = tmp_path / "todos.db"
    connect(core_db).close()
    from sb_todos.db import connect as connect_todos

    connect_todos(todos_db).close()
    _patch_conns(monkeypatch, core_db, todos_db)

    conn = connect(core_db)
    try:
        replace_mirror(
            conn,
            meetings=[],
            spaces=[],
            messages=[
                {
                    "id": "msg-1",
                    "space_id": "s1",
                    "space_name": "Release room",
                    "sender_name": "Ada",
                    "sender_email": "ada@example.com",
                    "is_dm": False,
                    "is_mention": True,
                    "is_unread": True,
                    "preview": "Can you check the release notes?",
                    "occurred_at": "2026-09-30T09:00:00Z",
                    "deep_link": "https://webex.example/msg-1",
                }
            ],
        )
    finally:
        conn.close()

    rows = tt.webex_attention_ranked()
    assert rows[0]["triage_kind"] == "mention"
    assert rows[0]["suggested_action_verb"] == "Discussed"
    assert rows[0]["staleness_hours"] is not None


def test_ranked_attention_drops_general_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A message that is not a mention, DM, or reply-to-me is dropped from
    the inbox entirely (Attention shows only those three kinds)."""
    core_db = tmp_path / "core.db"
    todos_db = tmp_path / "todos.db"
    connect(core_db).close()
    from sb_todos.db import connect as connect_todos

    connect_todos(todos_db).close()
    _patch_conns(monkeypatch, core_db, todos_db)

    conn = connect(core_db)
    try:
        replace_mirror(
            conn,
            meetings=[],
            spaces=[],
            messages=[
                {
                    "id": "msg-general",
                    "space_id": "s1",
                    "space_name": "Team room",
                    "sender_name": "Bo",
                    "is_dm": False,
                    "is_mention": False,
                    "is_unread": True,
                    "preview": "The build finished",
                    "occurred_at": "2026-09-30T09:00:00Z",
                }
            ],
        )
    finally:
        conn.close()

    rows = tt.webex_attention_ranked()
    assert rows == []


def test_ranked_attention_includes_reply_to_me_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reply-to-me message with no mention/dm flag still qualifies for
    Attention as its own third kind."""
    core_db = tmp_path / "core.db"
    todos_db = tmp_path / "todos.db"
    connect(core_db).close()
    from sb_todos.db import connect as connect_todos

    connect_todos(todos_db).close()
    _patch_conns(monkeypatch, core_db, todos_db)

    conn = connect(core_db)
    try:
        replace_mirror(
            conn,
            meetings=[],
            spaces=[],
            messages=[
                {
                    "id": "msg-reply",
                    "space_id": "s1",
                    "space_name": "Team room",
                    "sender_name": "Ada",
                    "is_dm": False,
                    "is_mention": False,
                    "is_unread": True,
                    "preview": "Sounds good",
                    "occurred_at": "2026-09-30T09:00:00Z",
                    "parent_message_id": "parent-1",
                    "parent_sender_email": "me@example.com",
                    "is_reply_to_me": True,
                }
            ],
        )
    finally:
        conn.close()

    rows = tt.webex_attention_ranked()
    assert [row["id"] for row in rows] == ["msg-reply"]
    assert rows[0]["triage_kind"] == "reply-to-me"
    assert rows[0]["suggested_action_verb"] == "Discussed"


def test_pre_meeting_context_returns_partial_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sb_todos import handlers
    from sb_todos.db import connect as connect_todos
    from sb_todos.models import TodoCreate

    core_db = tmp_path / "core.db"
    todos_db = tmp_path / "todos.db"
    connect(core_db).close()
    connect_todos(todos_db).close()
    _patch_conns(monkeypatch, core_db, todos_db)

    conn = connect(core_db)
    try:
        replace_mirror(
            conn,
            meetings=[
                {
                    "id": "meet-1",
                    "title": "Release review CXP-1",
                    "start": "2026-09-30T15:00:00Z",
                    "end": "2026-09-30T15:30:00Z",
                    "join_url": "https://webex.example/meet-1",
                    "attendees": [{"name": "Ada", "email": "ada@example.com"}],
                }
            ],
            spaces=[],
            messages=[
                {
                    "id": "msg-1",
                    "space_id": "s1",
                    "space_name": "Release room",
                    "sender_name": "Ada",
                    "sender_email": "ada@example.com",
                    "is_dm": False,
                    "is_mention": True,
                    "is_unread": True,
                    "preview": "Need review for CXP-1",
                    "occurred_at": "2026-09-30T14:50:00Z",
                    "deep_link": "https://webex.example/msg-1",
                }
            ],
        )
        append_ledger(
            conn,
            project="sb",
            summary="Reviewed Ada release notes for CXP-1",
            action_verb="Reviewed",
            refs=[{"kind": "jira", "value": "CXP-1"}],
            ts="2026-09-25T10:00:00Z",
        )
    finally:
        conn.close()

    todos_conn = connect_todos(todos_db)
    try:
        handlers.add_todo(
            todos_conn,
            TodoCreate(title="Prep release review notes", priority=1, domain="work"),
        )
    finally:
        todos_conn.close()

    result = tt.pre_meeting_context("meet-1")
    assert result["meeting"]["id"] == "meet-1"
    assert result["recent_messages"][0]["sender_name"] == "Ada"
    assert result["recent_ledger"][0]["summary"].startswith("Reviewed Ada")
    assert "CXP-1" in result["related_jiras"]
    assert result["open_todos"][0]["title"] == "Prep release review notes"


def test_propose_meeting_notes_falls_back_when_llm_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    core_db = tmp_path / "core.db"
    todos_db = tmp_path / "todos.db"
    connect(core_db).close()
    from sb_todos.db import connect as connect_todos

    connect_todos(todos_db).close()
    _patch_conns(monkeypatch, core_db, todos_db)
    monkeypatch.setattr(
        tt, "_llm_complete", lambda prompt: (_ for _ in ()).throw(RuntimeError("down"))
    )

    conn = connect(core_db)
    try:
        replace_mirror(
            conn,
            meetings=[
                {
                    "id": "meet-2",
                    "title": "Release review",
                    "start": "2026-09-30T15:00:00Z",
                    "end": "2026-09-30T15:30:00Z",
                    "join_url": "https://webex.example/meet-2",
                    "attendees": [{"name": "Ada", "email": "ada@example.com"}],
                }
            ],
            spaces=[],
            messages=[
                {
                    "id": "msg-2",
                    "space_id": "s1",
                    "space_name": "Release room",
                    "sender_name": "Ada",
                    "sender_email": "ada@example.com",
                    "is_dm": False,
                    "is_mention": False,
                    "is_unread": True,
                    "preview": "Wrapped the review",
                    "occurred_at": "2026-09-30T15:10:00Z",
                    "deep_link": "https://webex.example/msg-2",
                }
            ],
        )
    finally:
        conn.close()

    result = tt.propose_meeting_notes("meet-2")
    assert result["draft_count"] == 1

    conn = connect(core_db)
    try:
        proposals = daily_store.list_proposals(conn, status="pending")
    finally:
        conn.close()
    assert proposals[0]["type"] == "ledger_entry"
    assert "Discussed Release review" in proposals[0]["payload"]


def test_webex_attention_filtered_excludes_muted_spaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    core_db = tmp_path / "core.db"
    todos_db = tmp_path / "todos.db"
    connect(core_db).close()
    from sb_todos.db import connect as connect_todos

    connect_todos(todos_db).close()
    _patch_conns(monkeypatch, core_db, todos_db)

    conn = connect(core_db)
    try:
        replace_mirror(
            conn,
            meetings=[],
            spaces=[
                {"id": "s1", "name": "Loud room"},
                {"id": "s2", "name": "Muted room"},
            ],
            messages=[
                {
                    "id": "msg-1",
                    "space_id": "s1",
                    "space_name": "Loud room",
                    "sender_name": "Ada",
                    "is_mention": True,
                    "preview": "Can you check this?",
                    "occurred_at": "2026-09-30T09:00:00Z",
                },
                {
                    "id": "msg-2",
                    "space_id": "s2",
                    "space_name": "Muted room",
                    "sender_name": "Bo",
                    "is_mention": True,
                    "preview": "Can you check this too?",
                    "occurred_at": "2026-09-30T09:05:00Z",
                },
            ],
        )
        conn.execute("UPDATE sb_webex_spaces SET muted = 1 WHERE id = ?", ("s2",))
        conn.commit()
    finally:
        conn.close()

    all_rows = tt.webex_attention_ranked()
    assert {row["id"] for row in all_rows} == {"msg-1", "msg-2"}

    filtered_rows = tt.webex_attention_filtered()
    assert {row["id"] for row in filtered_rows} == {"msg-1"}
