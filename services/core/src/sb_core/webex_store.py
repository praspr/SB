"""Local Webex mirror. Message text is stored only as a short preview."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def replace_mirror(
    conn: sqlite3.Connection,
    *,
    meetings: list[dict],
    spaces: list[dict],
    messages: list[dict],
) -> dict[str, int]:
    synced = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM sb_webex_meetings")
        conn.execute("DELETE FROM sb_webex_spaces")
        conn.execute("DELETE FROM sb_webex_messages")
        for meeting in meetings:
            conn.execute(
                """
                INSERT INTO sb_webex_meetings
                  (id, title, start_at, end_at, join_url, organizer, attendees, agenda, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting["id"],
                    meeting["title"],
                    meeting.get("start") or "",
                    meeting.get("end") or "",
                    meeting.get("join_url") or None,
                    meeting.get("organizer") or None,
                    json.dumps(meeting.get("attendees") or []),
                    meeting.get("agenda") or None,
                    synced,
                ),
            )
        for space in spaces:
            conn.execute(
                """
                INSERT INTO sb_webex_spaces
                  (id, name, is_dm, unread_count, last_activity, members_count, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    space["id"],
                    space["name"],
                    int(bool(space.get("is_dm"))),
                    int(space.get("unread_count") or 0),
                    space.get("last_activity") or None,
                    int(space.get("members_count") or 0),
                    synced,
                ),
            )
        for message in messages[:200]:
            conn.execute(
                """
                INSERT INTO sb_webex_messages
                  (id, space_id, space_name, sender_name, sender_email, is_dm,
                   is_mention, is_unread, preview, occurred_at, deep_link, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message["id"],
                    message.get("space_id") or "",
                    message.get("space_name") or "Space",
                    message.get("sender_name") or "Someone",
                    message.get("sender_email") or None,
                    int(bool(message.get("is_dm"))),
                    int(bool(message.get("is_mention"))),
                    int(bool(message.get("is_unread"))),
                    (message.get("preview") or "")[:180],
                    message.get("occurred_at") or synced,
                    message.get("deep_link") or None,
                    synced,
                ),
            )
    except Exception:
        conn.rollback()
        raise
    conn.commit()
    return {
        "meetings": len(meetings),
        "spaces": len(spaces),
        "messages": min(len(messages), 200),
    }


def list_meetings(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM sb_webex_meetings ORDER BY start_at").fetchall()
    return [_meeting(row) for row in rows]


def list_spaces(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM sb_webex_spaces ORDER BY last_activity DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def list_messages(conn: sqlite3.Connection, space_id: str | None = None) -> list[dict]:
    if space_id:
        rows = conn.execute(
            "SELECT * FROM sb_webex_messages WHERE space_id = ? ORDER BY occurred_at DESC",
            (space_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sb_webex_messages ORDER BY occurred_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def _meeting(row: sqlite3.Row) -> dict:
    item = dict(row)
    try:
        item["attendees"] = json.loads(item.pop("attendees") or "[]")
    except json.JSONDecodeError:
        item["attendees"] = []
    item["start"] = item.pop("start_at")
    item["end"] = item.pop("end_at")
    return item
