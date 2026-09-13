"""Sanity checks that MCP tools are registered under the expected names."""

import asyncio

from sb_todos.mcp_tools import mcp

EXPECTED_TOOLS = {
    "todo_list",
    "todo_get",
    "todo_add",
    "todo_complete",
    "todo_uncomplete",
    "todo_update",
    "todo_delete",
    "todo_search",
}


def test_all_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS.issubset(names)


def test_tools_have_docstrings():
    tools = asyncio.run(mcp.list_tools())
    for tool in tools:
        if tool.name in EXPECTED_TOOLS:
            assert tool.description, f"tool {tool.name} missing a description"
