"""Comms-triage MCP helpers over the local Webex mirror, ledger, and proposals."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from fastmcp import FastMCP

from .store import daily as daily_store
from .store import ledger as ledger_store
from sb_webex.normalize import attention
from . import webex_store
from .webex_store import list_meetings, list_messages

mcp = FastMCP(
    "sb-triage",
    instructions=(
        "Read-only comms triage plus proposal drafting. Use the local Webex mirror, "
        "the ledger, and local proposals only."
    ),
)

_QUESTION_RE = re.compile(r"\?|\b(please|can you|could you|need|follow up)\b", re.I)
_JIRA_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
_STOP_WORDS = {"the", "and", "with", "from", "that", "this", "into", "about", "for", "your"}


def _get_conn() -> sqlite3.Connection:
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


def _get_todos_conn():
    from sb_todos.config import settings as todo_settings
    from sb_todos.db import connect as connect_todos

    return connect_todos(todo_settings.db_path)


def _llm_complete(prompt: str) -> str:
    from .config import settings
    from .llm import complete

    return complete(prompt, model=settings.llm_model)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(UTC)


def _hours_since(value: str | None) -> float | None:
    dt = _parse_dt(value)
    if dt is None:
        return None
    return round(max(0.0, (_now() - dt).total_seconds() / 3600), 1)


def _triage_kind(message: dict[str, Any]) -> str:
    preview = str(message.get("preview") or "")
    if bool(message.get("is_mention")):
        return "mention"
    if bool(message.get("is_dm")):
        return "dm"
    if _QUESTION_RE.search(preview):
        return "question"
    return "question"


def _suggested_action(kind: str) -> str:
    return "Discussed" if kind in {"mention", "dm", "question"} else "Reviewed"


def _title_keywords(title: str) -> list[str]:
    return [
        token for token in re.findall(r"[A-Za-z0-9-]{3,}", title.lower())
        if token not in _STOP_WORDS
    ]


def _meeting_payload(meeting: dict[str, Any] | None) -> dict[str, Any]:
    if not meeting:
        return {}
    return {
        "id": meeting.get("id"),
        "title": meeting.get("title") or "Meeting",
        "start_at": meeting.get("start") or "",
        "end_at": meeting.get("end") or "",
        "attendees": meeting.get("attendees") or [],
        "join_url": meeting.get("join_url") or None,
    }


def _message_overlaps(message: dict[str, Any], attendees: list[dict[str, Any]], keywords: list[str]) -> bool:
    sender_name = str(message.get("sender_name") or "").lower()
    sender_email = str(message.get("sender_email") or "").lower()
    space_name = str(message.get("space_name") or "").lower()
    attendee_names = {str(item.get("name") or "").lower() for item in attendees}
    attendee_emails = {str(item.get("email") or "").lower() for item in attendees}
    if sender_name and sender_name in attendee_names:
        return True
    if sender_email and sender_email in attendee_emails:
        return True
    return any(keyword in space_name for keyword in keywords)


def _entry_overlaps(entry: dict[str, Any], attendees: list[dict[str, Any]], keywords: list[str]) -> bool:
    blob = " ".join(
        [
            str(entry.get("summary") or ""),
            str(entry.get("body") or ""),
            " ".join(str(ref.get("value") or "") for ref in entry.get("refs") or [] if isinstance(ref, dict)),
        ]
    ).lower()
    for attendee in attendees:
        name = str(attendee.get("name") or "").lower()
        email = str(attendee.get("email") or "").lower()
        if name and name in blob:
            return True
        if email and email in blob:
            return True
    return any(keyword in blob for keyword in keywords)


def _recent_messages_for_meeting(conn: sqlite3.Connection, meeting: dict[str, Any]) -> list[dict[str, Any]]:
    attendees = meeting.get("attendees") or []
    keywords = _title_keywords(str(meeting.get("title") or ""))
    rows = list_messages(conn)
    filtered = [row for row in rows if _message_overlaps(row, attendees, keywords)]
    return sorted(filtered, key=lambda row: str(row.get("occurred_at") or ""), reverse=True)[:5]


def _recent_ledger_for_meeting(conn: sqlite3.Connection, meeting: dict[str, Any]) -> list[dict[str, Any]]:
    since = (_now() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
    candidates = ledger_store.search_ledger(conn, since=since, limit=200)
    attendees = meeting.get("attendees") or []
    keywords = _title_keywords(str(meeting.get("title") or ""))
    matched = [entry for entry in candidates if _entry_overlaps(entry, attendees, keywords)]
    project_counts = Counter(entry.get("project") for entry in matched if entry.get("project"))
    if project_counts:
        matched_project = project_counts.most_common(1)[0][0]
        matched = [entry for entry in matched if entry.get("project") == matched_project]
    return matched[:10]


def _related_jiras(entries: list[dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    for entry in entries:
        for ref in entry.get("refs") or []:
            if isinstance(ref, dict) and ref.get("kind") == "jira" and ref.get("value"):
                keys.append(str(ref["value"]))
        keys.extend(_JIRA_RE.findall(f"{entry.get('summary') or ''} {entry.get('body') or ''}"))
    return list(dict.fromkeys(keys))[:10]


def _open_todos_for_meeting(meeting: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from sb_todos import handlers as todo_handlers
    except Exception:  # noqa: BLE001
        return []

    keywords = _title_keywords(str(meeting.get("title") or ""))
    if not keywords:
        return []

    todos_conn = None
    try:
        todos_conn = _get_todos_conn()
        todos = todo_handlers.list_todos(todos_conn, status="open", limit=200)
    except Exception:  # noqa: BLE001
        return []
    finally:
        if todos_conn is not None:
            todos_conn.close()

    matched = []
    for todo in todos:
        blob = f"{getattr(todo, 'title', '')} {getattr(todo, 'description', '')}".lower()
        if any(keyword in blob for keyword in keywords):
            matched.append(
                {
                    "id": getattr(todo, "id", None),
                    "title": getattr(todo, "title", ""),
                    "priority": getattr(todo, "priority", None),
                }
            )
    return matched[:3]


def _meeting_messages_window(conn: sqlite3.Connection, meeting: dict[str, Any]) -> list[dict[str, Any]]:
    start = _parse_dt(str(meeting.get("start") or ""))
    end = _parse_dt(str(meeting.get("end") or ""))
    if start is None or end is None:
        return []
    window_start = start - timedelta(minutes=15)
    window_end = end + timedelta(minutes=30)
    attendees = meeting.get("attendees") or []
    keywords = _title_keywords(str(meeting.get("title") or ""))
    result: list[dict[str, Any]] = []
    for row in list_messages(conn):
        occurred = _parse_dt(str(row.get("occurred_at") or ""))
        if occurred is None or occurred < window_start or occurred > window_end:
            continue
        if _message_overlaps(row, attendees, keywords):
            result.append(row)
    return sorted(result, key=lambda row: str(row.get("occurred_at") or ""))


def _fallback_drafts(meeting: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    title = str(meeting.get("title") or "Meeting")
    meeting_id = str(meeting.get("id") or "")
    return (
        [
            {
                "title": f"Ledger entry · {title}",
                "payload": json.dumps(
                    {
                        "summary": f"Discussed {title}",
                        "action_verb": "Discussed",
                        "body": f"Meeting follow-up from {title}.",
                        "refs": [{"kind": "webex_meeting", "value": meeting_id}],
                    }
                ),
            }
        ],
        [],
    )


def _parse_llm_drafts(text: str, meeting: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return _fallback_drafts(meeting)
    if not isinstance(payload, dict):
        return _fallback_drafts(meeting)

    meeting_id = str(meeting.get("id") or "")
    ledger_entries: list[dict[str, Any]] = []
    todos: list[dict[str, Any]] = []

    for item in payload.get("ledger_entries") or []:
        if not isinstance(item, dict) or not item.get("summary"):
            continue
        ledger_entries.append(
            {
                "title": f"Ledger entry · {item.get('summary')}",
                "payload": json.dumps(
                    {
                        "summary": str(item.get("summary")),
                        "action_verb": str(item.get("action_verb") or "Discussed"),
                        "body": str(item.get("body") or ""),
                        "refs": [{"kind": "webex_meeting", "value": meeting_id}],
                    }
                ),
            }
        )

    for item in payload.get("todos") or []:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        todos.append(
            {
                "title": f"Todo · {item.get('title')}",
                "payload": json.dumps(
                    {
                        "title": str(item.get("title")),
                        "priority": int(item.get("priority") or 2),
                        "meeting_id": meeting_id,
                    }
                ),
            }
        )

    if not ledger_entries and not todos:
        return _fallback_drafts(meeting)
    return ledger_entries[:3], todos[:3]


@mcp.tool()
def webex_attention_ranked(limit: int = 30) -> list[dict[str, Any]]:
    """Return ranked Webex attention items with staleness and suggested verbs."""
    conn = _get_conn()
    try:
        ranked = attention(list_messages(conn))[: max(1, min(limit, 50))]
    finally:
        conn.close()

    return _decorate_attention(ranked)


@mcp.tool()
def webex_attention_filtered(limit: int = 30) -> list[dict[str, Any]]:
    """Ranked Webex attention items with messages from muted spaces removed.

    Wraps the same ranking as ``webex_attention_ranked`` but excludes any
    message whose ``space_id`` is currently muted (see ``webex_mute.py``).
    """
    conn = _get_conn()
    try:
        muted_ids = webex_store.list_muted_space_ids(conn)
        rows = [
            row for row in list_messages(conn) if row.get("space_id") not in muted_ids
        ]
        ranked = attention(rows)[: max(1, min(limit, 50))]
    finally:
        conn.close()

    return _decorate_attention(ranked)


def _decorate_attention(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in ranked:
        kind = _triage_kind(row)
        result.append(
            {
                **row,
                "triage_kind": kind,
                "staleness_hours": _hours_since(str(row.get("occurred_at") or "")),
                "suggested_action_verb": _suggested_action(kind),
            }
        )
    return result


@mcp.tool()
def pre_meeting_context(meeting_id: str) -> dict[str, Any]:
    """Return best-effort pre-meeting context from the local mirror and ledger."""
    conn = _get_conn()
    try:
        meeting = next((row for row in list_meetings(conn) if row.get("id") == meeting_id), None)
        if meeting is None:
            return {
                "meeting": {},
                "recent_messages": [],
                "recent_ledger": [],
                "related_jiras": [],
                "open_todos": [],
            }
        recent_messages = _recent_messages_for_meeting(conn, meeting)
        recent_ledger = _recent_ledger_for_meeting(conn, meeting)
    finally:
        conn.close()

    return {
        "meeting": _meeting_payload(meeting),
        "recent_messages": recent_messages,
        "recent_ledger": recent_ledger,
        "related_jiras": _related_jiras(recent_ledger),
        "open_todos": _open_todos_for_meeting(meeting),
    }


@mcp.tool()
def propose_meeting_notes(meeting_id: str) -> dict[str, Any]:
    """Draft ledger-entry and todo proposals from a recent meeting."""
    conn = _get_conn()
    try:
        meeting = next((row for row in list_meetings(conn) if row.get("id") == meeting_id), None)
        if meeting is None:
            return {"proposal_ids": [], "draft_count": 0}
        messages = _meeting_messages_window(conn, meeting)
        context_lines = [f"Meeting: {meeting.get('title')}"]
        context_lines.extend(
            f"- {row.get('sender_name')}: {row.get('preview')} [webex:{row.get('id')}]"
            for row in messages[:12]
        )
        prompt = (
            "Return strict JSON with keys ledger_entries and todos. ledger_entries must be "
            "1-3 dicts with summary, action_verb, body. todos must be 0-3 dicts with title "
            "and priority (1-4). Use only the meeting and message context below.\n\n"
            + "\n".join(context_lines)
        )
        try:
            llm_text = _llm_complete(prompt)
            ledger_drafts, todo_drafts = _parse_llm_drafts(llm_text, meeting)
        except Exception:  # noqa: BLE001
            ledger_drafts, todo_drafts = _fallback_drafts(meeting)

        proposal_ids: list[int] = []
        for draft in [*ledger_drafts, *todo_drafts]:
            kind = "ledger_entry" if draft in ledger_drafts else "todo"
            proposal = daily_store.create_proposal(
                conn,
                kind=kind,
                title=str(draft.get("title") or kind),
                payload=str(draft.get("payload") or ""),
            )
            proposal_ids.append(int(proposal["id"]))
        return {"proposal_ids": proposal_ids, "draft_count": len(proposal_ids)}
    finally:
        conn.close()
