"""Read-only Webex tools mounted on the unified sb MCP."""

from __future__ import annotations

import re

from fastmcp import FastMCP

from sb_webex.client import (
    McpClient,
    WebexAuthError,
    access_token,
    authenticated,
    begin_login,
)
from sb_webex.normalize import attention, meetings, messages, readable_tools, spaces

from . import llm
from .webex_store import list_meetings, list_messages, list_spaces, replace_mirror

mcp = FastMCP(
    "sb-webex",
    instructions=(
        "Read-only Webex mirror. Sync pulls meetings, spaces, and message "
        "previews. Never send messages or change meetings."
    ),
)

_CITATION_RE = re.compile(r"\[webex:([A-Za-z0-9+/=_-]+)\]")


def _conn():
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


def _pull(client: McpClient) -> dict[str, int]:
    catalog = readable_tools(client.list_tools())
    meeting_rows = (
        meetings(client.call_tool(catalog["meeting"])) if "meeting" in catalog else []
    )
    space_rows = (
        spaces(client.call_tool(catalog["space"])) if "space" in catalog else []
    )
    message_rows: list[dict] = []
    if "message" in catalog:
        if space_rows:
            for space in space_rows[:15]:
                payload = client.call_tool(catalog["message"], {"roomId": space["id"]})
                message_rows.extend(messages(payload, space_name=space["name"]))
        else:
            message_rows.extend(messages(client.call_tool(catalog["message"])))
    conn = _conn()
    try:
        return replace_mirror(
            conn, meetings=meeting_rows, spaces=space_rows, messages=message_rows
        )
    finally:
        conn.close()


@mcp.tool()
def webex_status() -> dict:
    """Return whether Webex sign-in is present. Never returns tokens."""
    conn = _conn()
    try:
        meeting_count = conn.execute(
            "SELECT COUNT(*) FROM sb_webex_meetings"
        ).fetchone()[0]
        message_count = conn.execute(
            "SELECT COUNT(*) FROM sb_webex_messages"
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        "authenticated": authenticated(),
        "meetings_count": meeting_count,
        "messages_count": message_count,
        "login_path": "/webex/login",
    }


@mcp.tool()
def webex_login_url() -> dict:
    """Return the OAuth URL for a one-time Webex sign-in."""
    from .config import settings

    redirect = f"http://{settings.host}:{settings.port}/webex/callback"
    return {"url": begin_login(redirect)}


@mcp.tool()
def sync_webex() -> dict:
    """Pull read-only Webex meetings, spaces, and message previews."""
    token = access_token()
    if not token:
        return {
            "meetings": 0,
            "spaces": 0,
            "messages": 0,
            "errors": ["Webex is not signed in. Open /webex/login."],
        }
    try:
        counts = _pull(McpClient(token))
    except WebexAuthError as exc:
        return {"meetings": 0, "spaces": 0, "messages": 0, "errors": [str(exc)]}
    return {**counts, "errors": []}


@mcp.tool()
def list_webex_meetings() -> list[dict]:
    """List mirrored Webex meetings. Read-only."""
    conn = _conn()
    try:
        return list_meetings(conn)
    finally:
        conn.close()


@mcp.tool()
def list_webex_spaces() -> list[dict]:
    """List mirrored Webex spaces. Read-only."""
    conn = _conn()
    try:
        return list_spaces(conn)
    finally:
        conn.close()


@mcp.tool()
def list_webex_messages(space_id: str | None = None) -> list[dict]:
    """List mirrored message previews. Full message bodies are not stored."""
    conn = _conn()
    try:
        return list_messages(conn, space_id=space_id)
    finally:
        conn.close()


@mcp.tool()
def webex_attention(limit: int = 20) -> list[dict]:
    """Rank mentions, direct messages, and questions that need attention."""
    conn = _conn()
    try:
        rows = list_messages(conn)
    finally:
        conn.close()
    return attention(rows)[: max(1, min(limit, 50))]


def _fallback_summary(rows: list[dict]) -> dict:
    selected = rows[:8]
    lines = ["Recent messages:"]
    lines.extend(
        f"- {row['sender_name']}: {row['preview']} [webex:{row['id']}]"
        for row in selected
    )
    return {
        "summary": "\n".join(lines),
        "citations": [f"[webex:{row['id']}]" for row in selected],
        "mode": "fallback",
    }


@mcp.tool()
def summarize_webex_space(space_id: str) -> dict:
    """Summarize one mirrored space. Every claim must cite [webex:<id>]."""
    conn = _conn()
    try:
        rows = list_messages(conn, space_id=space_id)
    finally:
        conn.close()
    if not rows:
        return {
            "summary": "No mirrored messages for that space.",
            "citations": [],
            "mode": "no_context",
        }
    context = "\n".join(
        f"[webex:{row['id']}] {row['sender_name']}: {row['preview']}"
        for row in rows[:30]
    )
    prompt = (
        "Summarize this Webex space for a daily briefing. Use only LOCAL_CONTEXT. "
        "Separate decisions, action items, blockers, and open questions. "
        "End every factual line with an exact [webex:<id>] citation from context. "
        "Do not draft or send a reply.\n\nLOCAL_CONTEXT\n"
        f"{context}\nEND_LOCAL_CONTEXT"
    )
    try:
        summary = llm.complete(prompt).strip()
    except llm.LLMUnavailable:
        return _fallback_summary(rows)
    allowed = {row["id"] for row in rows}
    cited = list(dict.fromkeys(_CITATION_RE.findall(summary)))
    if not cited or any(citation not in allowed for citation in cited):
        return _fallback_summary(rows)
    return {
        "summary": summary,
        "citations": [f"[webex:{citation}]" for citation in cited],
        "mode": "llm",
    }
