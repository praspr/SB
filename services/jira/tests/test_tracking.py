"""Persistent, pull-only tracking for JIRA issues outside the assigned JQL."""

from __future__ import annotations

import json

import pytest

from sb_jira import atlassian_client, mcp_tools, sync, tracking
from sb_jira.config import settings


def test_parse_accepts_a_key_and_configured_browse_url() -> None:
    site = "https://cisco-cxe.atlassian.net"
    assert tracking.parse_issue("cxp-123", site) == "CXP-123"
    assert tracking.parse_issue(f"{site}/browse/CXPL-9", site) == "CXPL-9"


def test_parse_rejects_foreign_hosts_and_non_issue_paths() -> None:
    site = "https://cisco-cxe.atlassian.net"
    with pytest.raises(ValueError, match="configured Atlassian site"):
        tracking.parse_issue("https://example.com/browse/CXP-1", site)
    with pytest.raises(ValueError, match="not a JIRA issue"):
        tracking.parse_issue(f"{site}/wiki/CXP-1", site)


def test_tracked_keys_are_atomic_unique_and_sorted(tmp_path) -> None:
    path = tmp_path / "tracked.json"
    tracking.add_key("CXP-2", path)
    tracking.add_key("CXP-2", path)
    tracking.add_key("CXP-10", path)
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 1,
        "keys": ["CXP-10", "CXP-2"],
    }
    tracking.remove_key("CXP-2", path)
    assert tracking.load_keys(path) == ["CXP-10"]


def test_fetch_issue_uses_get(monkeypatch) -> None:
    seen: dict = {}

    class Response:
        status_code = 200
        text = ""

        def json(self) -> dict:
            return {
                "key": "CXP-9",
                "fields": {
                    "summary": "Tracked issue",
                    "status": {"name": "Open"},
                    "priority": {"name": "High"},
                    "issuetype": {"name": "Bug"},
                    "assignee": {
                        "displayName": "Ada",
                        "emailAddress": "ada@example.com",
                    },
                    "created": "2026-09-01",
                    "updated": "2026-09-30",
                    "labels": [],
                    "fixVersions": [],
                },
            }

    class Client:
        def __init__(self, timeout: float | None = None) -> None:
            self.timeout = timeout

        def __enter__(self) -> "Client":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def get(
            self, url: str, headers: dict | None = None, params: dict | None = None
        ) -> Response:
            seen["url"] = url
            seen["params"] = params
            return Response()

        def post(self, *args: object, **kwargs: object) -> Response:
            raise AssertionError("JIRA integration must remain read-only")

    monkeypatch.setattr(atlassian_client, "get_token", lambda: "test-token")
    monkeypatch.setattr(atlassian_client.httpx, "Client", Client)
    ticket = atlassian_client.fetch_issue("CXP-9")
    assert ticket.key == "CXP-9"
    assert seen["url"].endswith("/rest/api/3/issue/CXP-9")
    assert "summary" in seen["params"]["fields"]


def test_track_jira_writes_the_mirror_and_keeps_it_on_sync(monkeypatch) -> None:
    def issue(key: str) -> dict:
        return {
            "key": key,
            "fields": {
                "summary": f"Issue {key}",
                "status": {"name": "Open"},
                "priority": {"name": "Medium"},
                "issuetype": {"name": "Task"},
                "created": "2026-09-01",
                "updated": "2026-09-30",
                "labels": [],
                "fixVersions": [],
            },
        }

    class Response:
        def __init__(self, payload: dict, status_code: int = 200) -> None:
            self.status_code = status_code
            self.text = ""
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    class Client:
        def __init__(self, timeout: float | None = None) -> None:
            self.timeout = timeout

        def __enter__(self) -> "Client":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def get(
            self, url: str, headers: dict | None = None, params: dict | None = None
        ) -> Response:
            if url.endswith("/rest/api/3/issue/CXP-77"):
                return Response(issue("CXP-77"))
            if url.endswith("/rest/api/3/issue/CXP-88"):
                return Response({}, status_code=404)
            return Response({"issues": [issue("CXP-1")], "isLast": True})

        def post(self, *args: object, **kwargs: object) -> Response:
            raise AssertionError("JIRA integration must remain read-only")

    monkeypatch.setattr(atlassian_client, "get_token", lambda: "test-token")
    monkeypatch.setattr(atlassian_client.httpx, "Client", Client)

    tracked = mcp_tools.track_jira("https://cisco-cxe.atlassian.net/browse/cxp-77")
    assert tracked["errors"] == []
    assert tracked["key"] == "CXP-77"
    assert (settings.tickets_dir / "CXP-77.md").is_file()

    result = sync.run_sync()
    assert "CXP-77" not in " ".join(result.errors)
    assert (settings.tickets_dir / "CXP-77.md").is_file()

    missing = mcp_tools.track_jira("CXP-88")
    assert missing["tracked"] is False
    assert any(
        "404" in error or "not found" in error.lower() for error in missing["errors"]
    )
    assert "CXP-88" not in tracking.load_keys(settings.tracked_path)
