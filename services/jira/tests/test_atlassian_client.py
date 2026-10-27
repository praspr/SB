"""The enhanced JQL search replaced the removed /rest/api/3/search endpoint."""

from __future__ import annotations

import pytest

from sb_jira import atlassian_client


def _issue(key: str) -> dict:
    return {
        "key": key,
        "fields": {
            "summary": key,
            "status": {"name": "Open"},
            "priority": {"name": "Medium"},
            "issuetype": {"name": "Bug"},
            "assignee": {
                "displayName": "PRASAD P R",
                "emailAddress": "praspr@cisco.com",
            },
            "created": "2026-09-01",
            "updated": "2026-09-29",
            "labels": [],
            "fixVersions": [],
        },
    }


def test_fetch_gets_search_jql_and_follows_next_page(monkeypatch):
    calls: list[dict] = []

    class Response:
        def __init__(self, payload: dict) -> None:
            self.status_code = 200
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
            assert url.endswith("/rest/api/3/search/jql")
            assert params is not None
            assert "startAt" not in params
            calls.append(params)
            if "nextPageToken" not in params:
                return Response(
                    {
                        "issues": [_issue("CXP-1")],
                        "isLast": False,
                        "nextPageToken": "page-2",
                    }
                )
            return Response({"issues": [_issue("CXP-2")], "isLast": True})

        def post(self, *args: object, **kwargs: object) -> Response:
            raise AssertionError("JIRA integration must remain read-only")

    monkeypatch.setattr(atlassian_client, "get_token", lambda: "test-token")
    monkeypatch.setattr(atlassian_client.httpx, "Client", Client)

    tickets = atlassian_client.fetch_all_assigned()

    assert [ticket.key for ticket in tickets] == ["CXP-1", "CXP-2"]
    assert calls[1]["nextPageToken"] == "page-2"
    assert "summary" in calls[0]["fields"]


def test_fetch_issue_rejects_malformed_key_before_any_http(monkeypatch):
    """L2: a crafted key must be rejected before building the request URL."""

    def _boom_token():
        raise AssertionError("get_token must not be reached for an invalid key")

    monkeypatch.setattr(atlassian_client, "get_token", _boom_token)

    for bad in ["../myself", "cxp-1", "CXP1", "", "CXP-", "CXP-1/../x"]:
        with pytest.raises(ValueError):
            atlassian_client.fetch_issue(bad)
