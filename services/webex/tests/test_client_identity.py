"""Tests for get_me() and get_message() (+ LRU cache) in sb_webex.client."""

from __future__ import annotations

import httpx
import pytest

from sb_webex import client


@pytest.fixture(autouse=True)
def _clear_message_cache():
    client._fetch_message_cached.cache_clear()
    yield
    client._fetch_message_cached.cache_clear()


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]

    def json(self) -> dict:
        return self._payload


def test_get_me_returns_email_and_display_name(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, headers=None, timeout=None):
        assert url == f"{client.WEBEX_API_BASE}/people/me"
        assert headers["Authorization"] == "Bearer tok-123"
        return _FakeResponse(200, {"emails": ["me@example.com"], "displayName": "Me Myself"})

    monkeypatch.setattr(httpx, "get", fake_get)
    result = client.McpClient("tok-123").get_me()
    assert result == {"email": "me@example.com", "display_name": "Me Myself"}


def test_get_me_returns_none_when_no_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, {"emails": []}))
    assert client.McpClient("tok").get_me() is None


def test_get_me_returns_none_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", fake_get)
    assert client.McpClient("tok").get_me() is None


def test_get_message_returns_person_email_and_text(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, headers=None, timeout=None):
        assert url == f"{client.WEBEX_API_BASE}/messages/msg-1"
        return _FakeResponse(
            200, {"id": "msg-1", "personEmail": "ada@example.com", "personDisplayName": "Ada", "text": "sure"}
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    result = client.McpClient("tok").get_message("msg-1")
    assert result == {
        "id": "msg-1",
        "personEmail": "ada@example.com",
        "personName": "Ada",
        "text": "sure",
    }


def test_get_message_returns_none_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(404))
    assert client.McpClient("tok").get_message("missing") is None


def test_get_message_returns_none_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", fake_get)
    assert client.McpClient("tok").get_message("msg-1") is None


def test_get_message_is_cached_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["count"] += 1
        return _FakeResponse(200, {"id": "msg-1", "personEmail": "ada@example.com"})

    monkeypatch.setattr(httpx, "get", fake_get)
    webex_client = client.McpClient("tok")
    first = webex_client.get_message("msg-1")
    second = webex_client.get_message("msg-1")
    assert first == second
    assert calls["count"] == 1


def test_get_message_cache_is_keyed_by_token(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["count"] += 1
        return _FakeResponse(200, {"id": "msg-1", "personEmail": "ada@example.com"})

    monkeypatch.setattr(httpx, "get", fake_get)
    client.McpClient("tok-a").get_message("msg-1")
    client.McpClient("tok-b").get_message("msg-1")
    assert calls["count"] == 2
