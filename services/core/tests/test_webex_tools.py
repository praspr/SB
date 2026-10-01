"""Read-only Webex sync never calls write-named tools."""

from __future__ import annotations

from sb_core.adapters.webex import run as index_webex
from sb_core.config import settings
from sb_core.store.db import connect
from sb_core.store.signals import search_signals
from sb_core.webex_store import get_identity, list_messages, replace_mirror
from sb_core.webex_tools import summarize_webex_space, sync_webex, webex_status


class _FakeClient:
    def __init__(self) -> None:
        self.called: list[str] = []
        self.arguments: dict[str, dict] = {}

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
        self.arguments[name] = arguments or {}
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
    assert "from_time" in fake.arguments["list_meetings"]
    assert "to_time" in fake.arguments["list_meetings"]
    assert fake.arguments["list_messages"]["room_ids"] == ["s1"]
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


class _IdentityFakeClient(_FakeClient):
    """Same fixtures as _FakeClient, plus get_me/get_message for identity and
    thread-reply enrichment coverage."""

    def __init__(self, *, me_email: str = "me@example.com", parent_sender: str = "me@example.com") -> None:
        super().__init__()
        self.me_email = me_email
        self.parent_sender = parent_sender
        self.get_me_calls = 0
        self.get_message_calls: list[str] = []

    def get_me(self) -> dict:
        self.get_me_calls += 1
        return {"email": self.me_email, "display_name": "Me Myself"}

    def get_message(self, message_id: str) -> dict | None:
        self.get_message_calls.append(message_id)
        return {"id": message_id, "personEmail": self.parent_sender, "personName": "Parent Sender"}


def _reset_identity(conn) -> None:
    conn.execute("DELETE FROM sb_webex_identity")
    conn.commit()


def test_sync_captures_identity_on_first_sync(monkeypatch) -> None:
    conn = connect(settings.db_path)
    try:
        _reset_identity(conn)
    finally:
        conn.close()

    fake = _IdentityFakeClient()
    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: "session")
    monkeypatch.setattr("sb_core.webex_tools.McpClient", lambda token: fake)

    sync_webex()

    conn = connect(settings.db_path)
    try:
        identity = get_identity(conn)
    finally:
        conn.close()
    assert identity is not None
    assert identity["email"] == "me@example.com"
    assert fake.get_me_calls == 1


def test_sync_does_not_refetch_identity_once_cached(monkeypatch) -> None:
    conn = connect(settings.db_path)
    try:
        _reset_identity(conn)
        from sb_core.webex_store import set_identity

        set_identity(conn, "already-cached@example.com", "Cached Person")
    finally:
        conn.close()

    fake = _IdentityFakeClient()
    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: "session")
    monkeypatch.setattr("sb_core.webex_tools.McpClient", lambda token: fake)

    sync_webex()

    assert fake.get_me_calls == 0


def test_sync_enriches_reply_to_me_from_parent_lookup(monkeypatch) -> None:
    conn = connect(settings.db_path)
    try:
        _reset_identity(conn)
    finally:
        conn.close()

    fake = _IdentityFakeClient(me_email="me@example.com", parent_sender="me@example.com")

    class _ReplyClient(_IdentityFakeClient):
        def call_tool(self, name: str, arguments: dict | None = None) -> dict:
            if name == "list_messages":
                return {
                    "items": [
                        {
                            "id": "msg-reply",
                            "roomId": "s1",
                            "text": "Sounds good",
                            "personDisplayName": "Ada",
                            "parentId": "parent-1",
                            "created": "2026-09-30T14:05:00Z",
                        }
                    ]
                }
            return super().call_tool(name, arguments)

    reply_client = _ReplyClient(me_email="me@example.com", parent_sender="me@example.com")
    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: "session")
    monkeypatch.setattr("sb_core.webex_tools.McpClient", lambda token: reply_client)

    sync_webex()

    conn = connect(settings.db_path)
    try:
        rows = list_messages(conn)
    finally:
        conn.close()
    reply_row = next(row for row in rows if row["id"] == "msg-reply")
    assert reply_row["parent_message_id"] == "parent-1"
    assert reply_row["parent_sender_email"] == "me@example.com"
    assert reply_row["is_reply_to_me"] == 1
    assert reply_client.get_message_calls == ["parent-1"]


def test_sync_does_not_mark_reply_to_me_when_parent_sender_differs(monkeypatch) -> None:
    conn = connect(settings.db_path)
    try:
        _reset_identity(conn)
    finally:
        conn.close()

    class _ReplyClient(_IdentityFakeClient):
        def call_tool(self, name: str, arguments: dict | None = None) -> dict:
            if name == "list_messages":
                return {
                    "items": [
                        {
                            "id": "msg-reply-2",
                            "roomId": "s1",
                            "text": "Thanks",
                            "personDisplayName": "Ada",
                            "parentId": "parent-2",
                            "created": "2026-09-30T14:10:00Z",
                        }
                    ]
                }
            return super().call_tool(name, arguments)

    reply_client = _ReplyClient(me_email="me@example.com", parent_sender="someone-else@example.com")
    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: "session")
    monkeypatch.setattr("sb_core.webex_tools.McpClient", lambda token: reply_client)

    sync_webex()

    conn = connect(settings.db_path)
    try:
        rows = list_messages(conn)
    finally:
        conn.close()
    reply_row = next(row for row in rows if row["id"] == "msg-reply-2")
    assert reply_row["parent_sender_email"] == "someone-else@example.com"
    assert reply_row["is_reply_to_me"] == 0


# ---------------------------------------------------------------------------
# webex_rethread (manual backfill; never auto-run)
# ---------------------------------------------------------------------------


def test_webex_rethread_backfills_unenriched_parent_rows(monkeypatch) -> None:
    from sb_core.webex_tools import webex_rethread

    conn = connect(settings.db_path)
    try:
        _reset_identity(conn)
        from sb_core.webex_store import set_identity

        set_identity(conn, "me@example.com", "Me Myself")
        replace_mirror(
            conn,
            meetings=[],
            spaces=[],
            messages=[
                {
                    "id": "msg-old",
                    "space_id": "s1",
                    "space_name": "Team",
                    "sender_name": "Ada",
                    "preview": "Old reply",
                    "occurred_at": "2026-09-20T09:00:00Z",
                    "parent_message_id": "parent-old",
                }
            ],
        )
    finally:
        conn.close()

    lookups: list[str] = []

    class _RethreadClient:
        def get_message(self, message_id: str) -> dict:
            lookups.append(message_id)
            return {"id": message_id, "personEmail": "me@example.com"}

    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: "session")
    monkeypatch.setattr("sb_core.webex_tools.McpClient", lambda token: _RethreadClient())

    result = webex_rethread()

    assert result["updated"] == 1
    assert result["checked"] == 1
    assert lookups == ["parent-old"]

    conn = connect(settings.db_path)
    try:
        rows = list_messages(conn)
    finally:
        conn.close()
    row = next(r for r in rows if r["id"] == "msg-old")
    assert row["parent_sender_email"] == "me@example.com"
    assert row["is_reply_to_me"] == 1


def test_webex_rethread_skips_already_enriched_rows(monkeypatch) -> None:
    from sb_core.webex_tools import webex_rethread

    conn = connect(settings.db_path)
    try:
        _reset_identity(conn)
        replace_mirror(
            conn,
            meetings=[],
            spaces=[],
            messages=[
                {
                    "id": "msg-enriched",
                    "space_id": "s1",
                    "space_name": "Team",
                    "sender_name": "Ada",
                    "preview": "Already enriched",
                    "occurred_at": "2026-09-20T09:00:00Z",
                    "parent_message_id": "parent-x",
                    "parent_sender_email": "someone@example.com",
                    "is_reply_to_me": False,
                },
                {
                    "id": "msg-no-parent",
                    "space_id": "s1",
                    "space_name": "Team",
                    "sender_name": "Bo",
                    "preview": "No parent",
                    "occurred_at": "2026-09-20T09:05:00Z",
                },
            ],
        )
    finally:
        conn.close()

    class _RethreadClient:
        def get_message(self, message_id: str) -> dict:
            raise AssertionError("must not look up already-enriched or parent-less rows")

    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: "session")
    monkeypatch.setattr("sb_core.webex_tools.McpClient", lambda token: _RethreadClient())

    result = webex_rethread()
    assert result["updated"] == 0
    assert result["checked"] == 0


def test_webex_rethread_continues_past_a_failed_lookup(monkeypatch) -> None:
    from sb_core.webex_tools import webex_rethread

    conn = connect(settings.db_path)
    try:
        _reset_identity(conn)
        replace_mirror(
            conn,
            meetings=[],
            spaces=[],
            messages=[
                {
                    "id": "msg-a",
                    "space_id": "s1",
                    "space_name": "Team",
                    "sender_name": "Ada",
                    "preview": "a",
                    "occurred_at": "2026-09-20T09:00:00Z",
                    "parent_message_id": "parent-a",
                },
                {
                    "id": "msg-b",
                    "space_id": "s1",
                    "space_name": "Team",
                    "sender_name": "Bo",
                    "preview": "b",
                    "occurred_at": "2026-09-20T09:01:00Z",
                    "parent_message_id": "parent-b",
                },
            ],
        )
    finally:
        conn.close()

    class _FlakyClient:
        def get_message(self, message_id: str) -> dict | None:
            if message_id == "parent-a":
                raise RuntimeError("network down")
            return {"id": message_id, "personEmail": "someone@example.com"}

    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: "session")
    monkeypatch.setattr("sb_core.webex_tools.McpClient", lambda token: _FlakyClient())

    result = webex_rethread()
    assert result["updated"] == 1
    assert result["checked"] == 2
    assert len(result["errors"]) == 1


def test_webex_rethread_without_sign_in_does_not_write(monkeypatch) -> None:
    from sb_core.webex_tools import webex_rethread

    monkeypatch.setattr("sb_core.webex_tools.access_token", lambda: None)
    monkeypatch.setattr(
        "sb_core.webex_tools.McpClient",
        lambda token: (_ for _ in ()).throw(AssertionError("no client")),
    )
    result = webex_rethread()
    assert result["updated"] == 0
    assert result["errors"]


# ---------------------------------------------------------------------------
# sync_webex — lock + record_sync wiring (phase 2j)
# ---------------------------------------------------------------------------


def test_sync_webex_records_sync_with_counts(monkeypatch) -> None:
    import sb_core.webex_tools as wt

    fake = _FakeClient()
    monkeypatch.setattr(wt, "access_token", lambda: "session")
    monkeypatch.setattr(wt, "McpClient", lambda token: fake)

    calls = []
    monkeypatch.setattr(
        wt, "record_sync", lambda adapter, counts, errors=None: calls.append(
            (adapter, counts, errors)
        )
    )

    result = sync_webex()

    assert len(calls) == 1
    adapter, counts, errors = calls[0]
    assert adapter == "webex"
    assert counts["meetings"] == 1
    assert counts["messages"] == 1
    assert errors is None
    assert result["meetings"] == 1


def test_sync_webex_already_running_returns_stub_and_does_not_log(monkeypatch) -> None:
    import sb_core.webex_tools as wt
    from contextlib import contextmanager

    @contextmanager
    def _fake_lock(name):
        yield False

    monkeypatch.setattr(wt, "sync_lock", _fake_lock)

    calls = []
    monkeypatch.setattr(wt, "record_sync", lambda *a, **kw: calls.append((a, kw)))
    monkeypatch.setattr(
        wt, "access_token", lambda: (_ for _ in ()).throw(AssertionError("must not run"))
    )

    result = sync_webex()
    assert result == {"status": "already_running", "meetings": 0, "spaces": 0, "messages": 0}
    assert calls == []
