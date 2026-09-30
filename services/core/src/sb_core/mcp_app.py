"""Foundation MCP surface for the standalone sb core service."""

from typing import Any

from fastmcp import FastMCP

from . import __version__
from .config import settings
from .store.db import connect, schema_version

mcp = FastMCP("sb")


def _mount_domains() -> None:
    """Mount domain tools in-process with their original names."""
    from sb_jira.mcp_tools import mcp as jira_mcp
    from sb_todos.mcp_tools import mcp as todos_mcp

    mcp.mount(todos_mcp)
    mcp.mount(jira_mcp)


_mount_domains()


async def system_status() -> dict[str, Any]:
    """Return a privacy-safe readiness summary for the local core service."""
    database_ready = False
    schema_version_value: int | None = None
    try:
        conn = connect(settings.db_path)
        try:
            conn.execute("SELECT 1").fetchone()
            schema_version_value = schema_version(conn)
            database_ready = True
        finally:
            conn.close()
    except Exception:
        database_ready = False
        schema_version_value = None

    tools = await mcp.list_tools()
    prompts = await mcp.list_prompts()
    resources = await mcp.list_resources()
    return {
        "status": "ok" if database_ready else "degraded",
        "version": __version__,
        "database": {
            "ready": database_ready,
            "schema_version": schema_version_value,
            "path": settings.db_path.expanduser().name,
        },
        "counts": {
            "tools": len(tools),
            "prompts": len(prompts),
            "resources": len(resources),
        },
    }


mcp.tool()(system_status)
