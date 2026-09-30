"""Mute/unmute MCP tools for the local Webex space mirror.

Kept separate from ``webex_tools.py`` (which is out of scope for this
phase) so mute state can be added without touching that file. Mute is
local-only UI state; it never calls Webex and never affects sync.
"""

from __future__ import annotations

import sqlite3

from fastmcp import FastMCP

from . import webex_store

mcp = FastMCP(
    "sb-webex-mute",
    instructions=(
        "Local-only mute state for Webex spaces. Never calls Webex; never "
        "changes what sync_webex pulls."
    ),
)


def _get_conn() -> sqlite3.Connection:
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


@mcp.tool()
def mute_space(space_id: str) -> dict:
    """Mute one Webex space in the local mirror. Attention and triage tools
    should stop surfacing messages from a muted space."""
    conn = _get_conn()
    try:
        return webex_store.set_space_muted(conn, space_id, True)
    finally:
        conn.close()


@mcp.tool()
def unmute_space(space_id: str) -> dict:
    """Unmute one Webex space in the local mirror."""
    conn = _get_conn()
    try:
        return webex_store.set_space_muted(conn, space_id, False)
    finally:
        conn.close()


@mcp.tool()
def list_muted_spaces() -> list[dict]:
    """List Webex spaces currently muted in the local mirror."""
    conn = _get_conn()
    try:
        return webex_store.list_muted_spaces(conn)
    finally:
        conn.close()
