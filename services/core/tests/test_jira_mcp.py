"""Pull-only JIRA tools mounted on the parent MCP."""

from __future__ import annotations

import ast
import asyncio
import inspect
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from sb_core.main import app
from sb_core.mcp_app import mcp

JIRA_TOOLS = {
    "list_jira_tickets",
    "get_jira_ticket",
    "sync_jira",
    "jira_status",
}
_WRITE_CALLS = {"post", "put", "patch", "delete"}


def _result(payload: object) -> object:
    structured = getattr(payload, "structured_content", None)
    if isinstance(structured, dict) and "result" in structured:
        return structured["result"]
    if structured is not None:
        return structured
    return payload


def test_parent_lists_jira_tools_without_a_namespace() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert JIRA_TOOLS <= names
    assert "sb-jira_list_jira_tickets" not in names


def test_no_atlassian_write_method_exists() -> None:
    import sb_jira.atlassian_client as client

    tree = ast.parse(inspect.getsource(client))
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)
    assert called.isdisjoint(_WRITE_CALLS)
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert names.isdisjoint(
        {
            "create_issue",
            "update_issue",
            "transition_issue",
            "delete_issue",
            "add_comment",
        }
    )


def test_health_does_not_probe_atlassian() -> None:
    with patch(
        "sb_jira.atlassian_client.probe_reachable",
        side_effect=AssertionError("health must not probe Atlassian"),
    ):
        with TestClient(app) as client:
            response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "token" not in response.text.lower()


def test_list_reads_local_mirror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sb_jira.config import settings

    fixture = Path(__file__).resolve().parents[2] / "jira" / "tests" / "fixtures"
    monkeypatch.setattr(settings, "tickets_dir", fixture)

    listed = _result(
        asyncio.run(mcp.call_tool("list_jira_tickets", {"q": "notification"}))
    )
    assert isinstance(listed, list)
    assert {item["key"] for item in listed} == {"CXP-46855"}
