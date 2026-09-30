"""Read-only Webex sync never calls write-named tools."""

from __future__ import annotations

from sb_core.adapters.webex import run as index_webex
from sb_core.config import settings
from sb_core.store.db import connect
from sb_core.store.signals import search_signals
from sb_core.webex_store import replace_mirror
from sb_core.webex_tools import summarize_webex_space, sync_webex, webex_status


class _FakeClient:
    def __init__(self) -> None:
        self.called: list[str] = []

    def list_tools(self) -> list[dict]:
        return [
            {"name": "list_meetings", "description": "List meetings"},
            {"name": "list_rooms", "description": "List spaces"},
            {"name": "list_messages", "description": "List messages"},
            {"name": "send_message", "description": "Send a message"},
            {"name": "schedule_meeting", "description": "Schedule a meeting"},
        ]

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        self.called.append(name)
        if name == "list_meetings":
            return {
                "items": [
                    {
                        "id": "m1",
                        "title": "Standup",
                        "start": "2026-09-30T15:00:00Z",
                        "end": "2026-09-30T15:30:00Z",
                    }
                ]
            }
        if name == "list_rooms":
            return {"items": [{"id": "s1", "title": "Team", "type": "group"}]}
        if name == "list_messages":
            return {
                "items": [
                    {
                        "id": "msg1",
                        "roomId": "s1",
                        "text": "Can you review the parser?",
                        "personDisplayName": "Ada",
                        "mentionedPeople": ["me"],
                        "created": "2026-09-30T14:00:00Z",
                    }
                ]
            }
        raise AssertionError(f"unexpected tool {name}")


def test_sync_skips_write_tools(monkeypatch) -> None:
    fake = _FakeClient()
    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: "session")
    monkeypatch.setattr("sb_core.webex_tools.McpClient", lambda token: fake)

    result = sync_webex()

    assert result["errors"] == []
    assert result["meetings"] == 1
    assert result["messages"] == 1
    assert "send_message" not in fake.called
    assert "schedule_meeting" not in fake.called
    status = webex_status()
    assert status["meetings_count"] == 1
    assert "token" not in str(status)


def test_sync_without_sign_in_does_not_call_webex(monkeypatch) -> None:
    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: None)
    monkeypatch.setattr(
        "sb_core.webex_tools.McpClient",
        lambda token: (_ for _ in ()).throw(AssertionError("no client")),
    )
    result = sync_webex()
    assert result["errors"]


def test_summary_falls_back_without_an_llm(monkeypatch) -> None:
    conn = connect(settings.db_path)
    try:
        replace_mirror(
            conn,
            meetings=[],
            spaces=[],
            messages=[
                {
                    "id": "msg1",
                    "space_id": "s1",
                    "space_name": "Team",
                    "sender_name": "Ada",
                    "preview": "Can you review the parser?",
                    "occurred_at": "2026-09-30T14:00:00Z",
                    "is_mention": True,
                }
            ],
        )
    finally:
        conn.close()

    def fail(prompt: str) -> str:
        from sb_core.llm import LLMUnavailable

        raise LLMUnavailable("down")

    monkeypatch.setattr("sb_core.webex_tools.llm.complete", fail)
    result = summarize_webex_space("s1")
    assert result["mode"] == "fallback"
    assert "[webex:msg1]" in result["citations"]


def test_webex_signals_are_idempotent() -> None:
    conn = connect(settings.db_path)
    try:
        replace_mirror(
            conn,
            meetings=[
                {
                    "id": "m1",
                    "title": "Standup",
                    "start": "2026-09-30T15:00:00Z",
                    "end": "2026-09-30T15:30:00Z",
                }
            ],
            spaces=[],
            messages=[
                {
                    "id": "msg1",
                    "space_id": "s1",
                    "space_name": "Team",
                    "sender_name": "Ada",
                    "preview": "Can you review?",
                    "occurred_at": "2026-09-30T14:00:00Z",
                    "is_mention": True,
                }
            ],
        )
        assert index_webex(conn) == 2
        assert index_webex(conn) == 2
        signals = search_signals(conn, source="webex")
        assert len(signals) == 2
    finally:
        conn.close()
