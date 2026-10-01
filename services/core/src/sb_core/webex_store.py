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
        muted_ids = {
            row["id"]
            for row in conn.execute(
                "SELECT id FROM sb_webex_spaces WHERE muted = 1"
            ).fetchall()
        }
        handled_by_id = {
            row["id"]: {
                "handled_at": row["handled_at"],
                "handled_action": row["handled_action"],
            }
            for row in conn.execute(
                "SELECT id, handled_at, handled_action FROM sb_webex_messages "
                "WHERE handled_at IS NOT NULL OR handled_action IS NOT NULL"
            ).fetchall()
        }
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
                  (id, name, is_dm, unread_count, last_activity, members_count, synced_at, muted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    space["id"],
                    space["name"],
                    int(bool(space.get("is_dm"))),
                    int(space.get("unread_count") or 0),
                    space.get("last_activity") or None,
                    int(space.get("members_count") or 0),
                    synced,
                    1 if space["id"] in muted_ids else 0,
                ),
            )
        for message in messages[:200]:
            conn.execute(
                """
                INSERT INTO sb_webex_messages
                  (id, space_id, space_name, sender_name, sender_email, is_dm,
                   is_mention, is_unread, preview, occurred_at, deep_link, synced_at,
                   parent_message_id, parent_sender_email, is_reply_to_me,
                   handled_at, handled_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    message.get("parent_message_id") or None,
                    message.get("parent_sender_email") or None,
                    int(bool(message.get("is_reply_to_me"))),
                    handled_by_id.get(message["id"], {}).get("handled_at"),
                    handled_by_id.get(message["id"], {}).get("handled_action"),
                )
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


def set_message_handled(conn: sqlite3.Connection, message_id: str, action: str) -> None:
    conn.execute(
        "UPDATE sb_webex_messages SET handled_at = ?, handled_action = ? WHERE id = ?",
        (_now(), action, message_id),
    )
    conn.commit()


def clear_message_handled(conn: sqlite3.Connection, message_id: str) -> None:
    conn.execute(
        "UPDATE sb_webex_messages SET handled_at = NULL, handled_action = NULL WHERE id = ?",
        (message_id,),
    )
    conn.commit()


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


def set_space_muted(conn: sqlite3.Connection, space_id: str, muted: bool) -> dict:
    """Set the muted flag on one space. Idempotent; returns the updated row,
    or ``{"id": space_id, "muted": muted, "found": False}`` if the space is
    not present in the local mirror (mute state still recorded for when it
    reappears is out of scope here -- the row simply does not exist yet)."""
    conn.execute(
        "UPDATE sb_webex_spaces SET muted = ? WHERE id = ?",
        (1 if muted else 0, space_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM sb_webex_spaces WHERE id = ?", (space_id,)
    ).fetchone()
    if row is None:
        return {"id": space_id, "muted": muted, "found": False}
    result = dict(row)
    result["muted"] = bool(result["muted"])
    result["found"] = True
    return result


def list_muted_space_ids(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT id FROM sb_webex_spaces WHERE muted = 1").fetchall()
    return {row["id"] for row in rows}


def list_muted_spaces(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM sb_webex_spaces WHERE muted = 1 ORDER BY name"
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["muted"] = bool(item["muted"])
        result.append(item)
    return result


def get_identity(conn: sqlite3.Connection) -> dict | None:
    """Return the cached ``{email, display_name, cached_at}`` for the
    signed-in Webex user, or None if identity has never been captured."""
    row = conn.execute("SELECT * FROM sb_webex_identity LIMIT 1").fetchone()
    return dict(row) if row is not None else None


def set_identity(conn: sqlite3.Connection, email: str, display_name: str) -> dict:
    """Cache the signed-in Webex user's identity. Single-row table: any
    existing identity is replaced (a fresh sign-in supersedes the old one)."""
    conn.execute("DELETE FROM sb_webex_identity")
    conn.execute(
        "INSERT INTO sb_webex_identity (email, display_name, cached_at) VALUES (?, ?, ?)",
        (email, display_name, _now()),
    )
    conn.commit()
    return {"email": email, "display_name": display_name, "cached_at": _now()}


def _meeting(row: sqlite3.Row) -> dict:
    item = dict(row)
    try:
        item["attendees"] = json.loads(item.pop("attendees") or "[]")
    except json.JSONDecodeError:
        item["attendees"] = []
    item["start"] = item.pop("start_at")
    item["end"] = item.pop("end_at")
    return item
