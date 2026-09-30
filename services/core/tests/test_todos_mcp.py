"""Todos tools mounted on the parent MCP, executed against an isolated database."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from sb_core.mcp_app import mcp

TODO_TOOLS = {
    "todo_list",
    "todo_get",
    "todo_add",
    "todo_complete",
    "todo_uncomplete",
    "todo_update",
    "todo_delete",
    "todo_search",
}


def _result(payload: object) -> object:
    structured = getattr(payload, "structured_content", None)
    if isinstance(structured, dict) and "result" in structured:
        return structured["result"]
    if structured is not None:
        return structured
    return payload


def test_parent_lists_todo_tools_without_a_namespace() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert TODO_TOOLS <= names
    assert not any(name.startswith("todos_") for name in names)


def test_add_list_complete_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sb_todos.config import settings

    monkeypatch.setattr(settings, "db_path", tmp_path / "todos.db")

    async def scenario() -> None:
        created = _result(
            await mcp.call_tool("todo_add", {"title": "Ship the MCP", "priority": 1})
        )
        assert isinstance(created, dict)
        assert created["title"] == "Ship the MCP"
        todo_id = created["id"]

        listed = _result(await mcp.call_tool("todo_list", {"status": "open"}))
        assert isinstance(listed, list)
        assert any(item["id"] == todo_id for item in listed)

        completed = _result(await mcp.call_tool("todo_complete", {"todo_id": todo_id}))
        assert isinstance(completed, dict)
        assert completed["is_completed"] is True

        found = _result(await mcp.call_tool("todo_search", {"query": "Ship"}))
        assert isinstance(found, list)
        assert any(item["id"] == todo_id for item in found)

    asyncio.run(scenario())
