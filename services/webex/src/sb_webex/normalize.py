"""Turn hosted Webex MCP results into dashboard records.

Tool names are discovered at runtime. Write-capable tools are refused even
when the OAuth server offers write scopes.
"""

from __future__ import annotations

import re
from typing import Any

_WRITE_TOOL = re.compile(
    r"send|create|update|delete|post|reply|write|invite|remove|schedule",
    re.IGNORECASE,
)


def readable_tools(tools: list[dict]) -> dict[str, str]:
    """Pick one read tool each for meetings, spaces, and messages."""
    chosen: dict[str, str] = {}
    for tool in tools:
        name = str(tool.get("name") or "")
        if not name or _WRITE_TOOL.search(name):
            continue
        blob = f"{name} {tool.get('description') or ''}"
        if "meeting" in blob.lower() and "meeting" not in chosen:
            chosen["meeting"] = name
        elif re.search(r"space|room", blob, re.IGNORECASE) and "space" not in chosen:
            chosen["space"] = name
        elif "message" in blob.lower() and "message" not in chosen:
            chosen["message"] = name
    return chosen


def _items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "meetings", "rooms", "spaces", "messages", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if any(key in payload for key in ("id", "title", "text")):
            return [payload]
    return []


def _first(item: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def meetings(payload: Any) -> list[dict]:
    rows = []
    for item in _items(payload):
        meeting_id = _first(item, "id", "meetingId")
        if not meeting_id:
            continue
        attendees = item.get("attendees") or item.get("invitees") or []
        if isinstance(attendees, list):
            people = [
                (
                    person
                    if isinstance(person, dict)
                    else {"name": str(person), "email": ""}
                )
                for person in attendees[:20]
            ]
        else:
            people = []
        rows.append(
            {
                "id": meeting_id,
                "title": _first(item, "title", "topic", "subject", default="Meeting"),
                "start": _first(item, "start", "start_at", "startTime"),
                "end": _first(item, "end", "end_at", "endTime"),
                "join_url": _first(
                    item, "webLink", "join_url", "joinUrl", "sipAddress"
                ),
                "organizer": _first(item, "hostEmail", "hostDisplayName", "organizer"),
                "attendees": people,
                "agenda": _first(item, "agenda", "description")[:1000],
            }
        )
    return rows


def spaces(payload: Any) -> list[dict]:
    rows = []
    for item in _items(payload):
        space_id = _first(item, "id", "roomId")
        if not space_id:
            continue
        room_type = _first(item, "type", "roomType").lower()
        rows.append(
            {
                "id": space_id,
                "name": _first(item, "title", "name", default="Space"),
                "is_dm": room_type == "direct" or bool(item.get("is_dm")),
                "unread_count": int(
                    item.get("unread_count") or item.get("unreadCount") or 0
                ),
                "last_activity": _first(
                    item, "lastActivity", "last_activity", "created"
                ),
                "members_count": int(
                    item.get("members_count") or item.get("membersCount") or 0
                ),
            }
        )
    return rows


def _message_items(payload: Any) -> list[dict]:
    """Accept a flat list or a map of room id to ``{messages: [...]}``."""
    if isinstance(payload, dict):
        grouped: list[dict] = []
        for room_id, body in payload.items():
            if not isinstance(body, dict) or not isinstance(body.get("messages"), list):
                continue
            for item in body["messages"]:
                if not isinstance(item, dict):
                    continue
                row = dict(item)
                row.setdefault("roomId", room_id)
                grouped.append(row)
        if grouped:
            return grouped
    return _items(payload)


def messages(payload: Any, *, space_name: str = "") -> list[dict]:
    rows = []
    for item in _message_items(payload):
        message_id = _first(item, "id", "messageId")
        if not message_id:
            continue
        text = _first(item, "text", "preview", "markdown", "content")
        mentions = item.get("mentionedPeople") or item.get("mentions") or []
        rows.append(
            {
                "id": message_id,
                "space_id": _first(item, "roomId", "space_id", "spaceId"),
                "space_name": _first(
                    item, "roomTitle", "space", default=space_name or "Space"
                ),
                "sender_name": _first(
                    item,
                    "personDisplayName",
                    "sender_name",
                    "personEmail",
                    default="Someone",
                ),
                "sender_email": _first(item, "personEmail", "sender_email"),
                "is_dm": _first(item, "roomType").lower() == "direct"
                or bool(item.get("is_dm")),
                "is_mention": bool(mentions) or bool(item.get("is_mention")),
                "is_unread": bool(item.get("is_unread", True)),
                "preview": " ".join(text.split())[:180],
                "occurred_at": _first(item, "created", "occurred_at", "published"),
                "deep_link": _first(item, "webUrl", "url", "deep_link"),
            }
        )
    return rows


def attention(message_rows: list[dict]) -> list[dict]:
    """Rank mentions and direct questions ahead of general space traffic."""

    def score(item: dict) -> tuple[int, str]:
        preview = item.get("preview") or ""
        rank = 0
        if item.get("is_mention"):
            rank += 4
        if item.get("is_dm"):
            rank += 3
        if "?" in preview or re.search(
            r"\b(please|can you|could you|need)\b", preview, re.I
        ):
            rank += 2
        if item.get("is_unread"):
            rank += 1
        return (rank, item.get("occurred_at") or "")

    return sorted(message_rows, key=score, reverse=True)
