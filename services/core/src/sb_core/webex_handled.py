"""Handled/unhandled MCP tools for the local Webex message mirror."""

from __future__ import annotations

import sqlite3

from fastmcp import FastMCP

from . import webex_store

mcp = FastMCP(
    "sb-webex-handled",
    instructions=(
        "Local-only handled state for Webex attention items. Never calls Webex; "
        "only updates the local mirror."
    ),
)

_VALID_ACTIONS = {"completed", "ignored"}


def _get_conn() -> sqlite3.Connection:
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


@mcp.tool()
def webex_mark_handled(message_id: str, action: str = "completed") -> dict:
    """Mark one mirrored Webex message handled with a local action."""
    if action not in _VALID_ACTIONS:
        raise ValueError("action must be one of: completed, ignored")
    conn = _get_conn()
    try:
        webex_store.set_message_handled(conn, message_id, action)
        return {"ok": True, "message_id": message_id, "action": action}
    finally:
        conn.close()


@mcp.tool()
def webex_mark_unhandled(message_id: str) -> dict:
    """Clear handled state from one mirrored Webex message."""
    conn = _get_conn()
    try:
        webex_store.clear_message_handled(conn, message_id)
        return {"ok": True, "message_id": message_id}
    finally:
        conn.close()
