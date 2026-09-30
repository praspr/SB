"""Foundation MCP surface for the standalone sb core service."""

from typing import Any

from fastmcp import FastMCP

from . import __version__
from .config import settings
from .store.db import connect, schema_version

mcp = FastMCP(
    "sb",
    instructions=(
        "Before using a skill's listed tools, discover that skill with list_skills "
        "or get_skill and follow its procedure. Do not invent tools that the skill "
        "does not list."
    ),
)


def _mount_domains() -> None:
    """Mount domain tools in-process with their original names."""
    from sb_jira.mcp_tools import mcp as jira_mcp
    from sb_todos.mcp_tools import mcp as todos_mcp

    mcp.mount(todos_mcp)
    mcp.mount(jira_mcp)
    from .chat_tools import mcp as chat_mcp
    from .goals_tools import mcp as goals_mcp
    from .jira_bulk import mcp as jira_bulk_mcp
    from .ledger_tools import mcp as ledger_mcp
    from .reports_tools import mcp as reports_mcp
    from .scheduler import mcp as scheduler_mcp
    from .skills import register_skill_tools
    from .ritual_tools import mcp as ritual_mcp
    from .sync_tools import mcp as sync_mcp
    from .triage_tools import mcp as triage_mcp
    from .url_hints import mcp as url_hints_mcp
    from .webex_mute import mcp as webex_mute_mcp
    from .webex_tools import mcp as webex_mcp

    register_skill_tools(mcp)
    mcp.mount(chat_mcp)
    mcp.mount(sync_mcp)
    mcp.mount(ritual_mcp)
    mcp.mount(webex_mcp)
    mcp.mount(webex_mute_mcp)
    mcp.mount(triage_mcp)
    mcp.mount(ledger_mcp)
    mcp.mount(reports_mcp)
    mcp.mount(goals_mcp)
    mcp.mount(scheduler_mcp)
    mcp.mount(url_hints_mcp)
    mcp.mount(jira_bulk_mcp)

    _seed_ledger_registry()


def _seed_ledger_registry() -> None:
    """Seed the ledger project registry on first run, using a fresh short-lived
    connection. No-op if the registry already has rows."""
    from .config import seed_registry_if_empty, settings
    from .store.db import connect

    conn = connect(settings.db_path)
    try:
        seed_registry_if_empty(conn)
    finally:
        conn.close()


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
