"""Read-only Webex tools mounted on the unified sb MCP."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

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
from .sync_logger import record_sync, sync_lock
from .webex_store import (
    get_identity,
    list_meetings,
    list_messages,
    list_spaces,
    replace_mirror,
    set_identity,
)

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


def _meeting_window() -> tuple[str, str]:
    """Local calendar today through the next 7 days, with a timezone offset."""
    start = (
        datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    )
    end = start + timedelta(days=7)
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


def _tool_error(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    code = payload.get("status_code")
    if isinstance(code, int) and code >= 400:
        detail = payload.get("message") or payload.get("error") or ""
        return f"Webex tool returned status {code} {detail}".strip()
    return None


def _ensure_identity(conn, client: McpClient) -> str | None:
    """Return the cached "me" email, fetching and persisting it once if the
    identity table is empty. Never raises -- a failed lookup just means
    reply-to-me enrichment stays off for this sync."""
    existing = get_identity(conn)
    if existing is not None:
        return str(existing["email"]) or None
    get_me = getattr(client, "get_me", None)
    if get_me is None:
        return None
    try:
        me = get_me()
    except Exception:  # noqa: BLE001
        return None
    if not me or not me.get("email"):
        return None
    set_identity(conn, str(me["email"]), str(me.get("display_name") or ""))
    return str(me["email"])


def _pull(client: McpClient) -> dict:
    catalog = readable_tools(client.list_tools())
    errors: list[str] = []
    meeting_rows: list[dict] = []
    if "meeting" in catalog:
        from_time, to_time = _meeting_window()
        payload = client.call_tool(
            catalog["meeting"],
            {"from_time": from_time, "to_time": to_time, "max": 100},
        )
        error = _tool_error(payload)
        if error:
            errors.append(error)
        meeting_rows = meetings(payload)
    space_rows = (
        spaces(client.call_tool(catalog["space"])) if "space" in catalog else []
    )
    conn = _conn()
    try:
        me_email = _ensure_identity(conn, client)
    finally:
        conn.close()

    message_rows: list[dict] = []
    if "message" in catalog and space_rows:
        room_ids = [space["id"] for space in space_rows[:15]]
        payload = client.call_tool(
            catalog["message"],
            {"room_ids": room_ids, "max": 20},
        )
        error = _tool_error(payload)
        if error:
            errors.append(error)
        message_rows = messages(
            payload, me_email=me_email, parent_lookup=getattr(client, "get_message", None)
        )
        names = {space["id"]: space["name"] for space in space_rows}
        for row in message_rows:
            row["space_name"] = names.get(row.get("space_id") or "", row["space_name"])
    conn = _conn()
    try:
        counts = replace_mirror(
            conn, meetings=meeting_rows, spaces=space_rows, messages=message_rows
        )
    finally:
        conn.close()
    return {**counts, "errors": errors}


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
    with sync_lock("webex") as acquired:
        if not acquired:
            return {
                "status": "already_running",
                "meetings": 0,
                "spaces": 0,
                "messages": 0,
            }

        token = access_token()
        if not token:
            result = {
                "meetings": 0,
                "spaces": 0,
                "messages": 0,
                "errors": ["Webex is not signed in. Open /webex/login."],
            }
            record_sync("webex", result, result.get("errors"))
            return result
        try:
            result = _pull(McpClient(token))
        except WebexAuthError as exc:
            result = {"meetings": 0, "spaces": 0, "messages": 0, "errors": [str(exc)]}
        record_sync("webex", result, result.get("errors") or None)
        return result


@mcp.tool()
def webex_rethread(limit: int = 500) -> dict:
    """Manual backfill: fill parent_sender_email/is_reply_to_me for older
    mirrored messages that have a parent_message_id but were never enriched.

    ``sync_webex`` only enriches newly-pulled messages (see locked design
    decision 5) to avoid ballooning a sync with parent lookups. This tool is
    a deliberate, manually-triggered repair path over the existing mirror --
    it is never auto-run. Read-only against Webex (GET only); the only
    writes are to the local mirror's thread columns.
    """
    token = access_token()
    if not token:
        return {"updated": 0, "checked": 0, "errors": ["Webex is not signed in. Open /webex/login."]}

    client = McpClient(token)
    conn = _conn()
    try:
        identity = get_identity(conn)
        me_email = str(identity["email"]) if identity else None

        rows = conn.execute(
            """
            SELECT id, parent_message_id FROM sb_webex_messages
            WHERE parent_message_id IS NOT NULL AND parent_sender_email IS NULL
            ORDER BY occurred_at DESC
            LIMIT ?
            """,
            (max(1, min(limit, 500)),),
        ).fetchall()

        updated = 0
        errors: list[str] = []
        for row in rows:
            try:
                parent = client.get_message(row["parent_message_id"])
            except Exception as exc:  # noqa: BLE001 -- one bad lookup must not stop the loop
                errors.append(f"{row['parent_message_id']}: {exc}")
                continue
            if not parent:
                continue
            sender = str(parent.get("personEmail") or "") or None
            is_reply = bool(me_email and sender and sender == me_email)
            conn.execute(
                "UPDATE sb_webex_messages SET parent_sender_email = ?, is_reply_to_me = ? WHERE id = ?",
                (sender, 1 if is_reply else 0, row["id"]),
            )
            updated += 1
        conn.commit()
        return {"updated": updated, "checked": len(rows), "errors": errors}
    finally:
        conn.close()


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
