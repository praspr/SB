"""Index the local Webex mirror into the signal ledger. Does not call Webex."""

from __future__ import annotations

import sqlite3

from ..store.signals import upsert_signal
from ..webex_store import list_meetings, list_messages


def run(core_conn: sqlite3.Connection) -> int:
    count = 0
    for meeting in list_meetings(core_conn):
        upsert_signal(
            core_conn,
            source="webex",
            source_id=f"meeting:{meeting['id']}",
            kind="meeting",
            occurred_at=meeting.get("start") or "",
            title=meeting["title"],
            body=meeting.get("agenda") or None,
            refs=[meeting["join_url"]] if meeting.get("join_url") else [],
        )
        count += 1
    for message in list_messages(core_conn):
        if not (message.get("is_mention") or message.get("is_dm")):
            continue
        upsert_signal(
            core_conn,
            source="webex",
            source_id=f"message:{message['id']}",
            kind="message",
            occurred_at=message.get("occurred_at") or "",
            title=f"{message['sender_name']}: {message['preview']}",
            scope=message.get("space_name"),
            refs=[f"webex:{message['id']}"],
        )
        count += 1
    return count
