"""Tests for webex_post.py: explicit posting wrapper only."""

from __future__ import annotations

import asyncio

import sb_core.webex_post as wp


class _FakeClient:
    def __init__(self, token: str) -> None:
        self.token = token
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        self.calls.append((name, arguments or {}))
        return {"id": "msg-1"}


def test_webex_post_tool_is_registered_and_mounted() -> None:
    names = {tool.name for tool in asyncio.run(wp.mcp.list_tools())}
    assert "webex_post_message" in names

    from sb_core.mcp_app import mcp as parent

    mounted = {tool.name for tool in asyncio.run(parent.list_tools())}
    assert "webex_post_message" in mounted


def test_webex_post_message_calls_hosted_tool(monkeypatch) -> None:
    fake = _FakeClient("token")
    monkeypatch.setattr(wp, "access_token", lambda: "token")
    monkeypatch.setattr(wp, "McpClient", lambda token: fake)

    result = wp.webex_post_message("space-1", "hello", "markdown")

    assert result["posted"] is True
    assert fake.calls == [
        (
            "post_webex_message",
            {"space_id": "space-1", "markdown": "hello", "message_type": "markdown"},
        )
    ]


def test_webex_post_message_reports_missing_sign_in(monkeypatch) -> None:
    monkeypatch.setattr(wp, "access_token", lambda: None)
    result = wp.webex_post_message("space-1", "hello")
    assert result["posted"] is False
    assert "not signed in" in result["error"]
