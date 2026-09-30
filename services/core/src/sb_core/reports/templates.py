"""Deterministic markdown report builders over the narrative ledger.

Every report is LLM-optional: the markdown structure, grouping, and
citation list are always computed deterministically from ``sb_ledger`` rows.
``query()`` is the only one that may additionally ask the LLM for a narrated
paragraph; if that backend is unavailable (or explicitly disabled), it falls
back to the same deterministic grouped-list shape used everywhere else.

Citation slots are rendered as ``[ledger:<id>]``, one per referenced row.
"""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from ..store.ledger import open_threads, search_ledger


def _utc_midnight(d: date) -> str:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _entry_date(entry: dict) -> str:
    ts = entry.get("ts") or ""
    return ts[:10] if len(ts) >= 10 else ""


def _citation_line(entry: dict) -> str:
    scope = f" — *`{entry['scope']}`*" if entry.get("scope") else ""
    return f"- **{entry.get('action_verb', 'Note')}** {entry.get('summary', '')}{scope} [ledger:{entry['id']}]"


def _open_threads_section(conn: sqlite3.Connection, *, project: Optional[str]) -> tuple[list[str], list[int]]:
    threads = open_threads(conn, project=project)
    if not threads:
        return [], []
    lines = ["", "## Open threads", ""]
    citations: list[int] = []
    for entry in threads:
        lines.append(_citation_line(entry))
        citations.append(entry["id"])
    return lines, citations


def _metadata_block(*, range_from: str, range_to: str, project: Optional[str]) -> list[str]:
    scope_line = f"Project: `{project}`" if project else "Project: all"
    return ["", f"Range: {range_from} → {range_to}  ·  {scope_line}", ""]


# ---------------------------------------------------------------------------
# daily
# ---------------------------------------------------------------------------


def daily(
    conn: sqlite3.Connection,
    *,
    target_date: Optional[date] = None,
    project: Optional[str] = None,
) -> dict:
    """Report FOR *target_date* (default today): yesterday's ledger entries
    grouped by project + scope, plus today's meetings and top open todos.

    Returns ``{"markdown", "citations", "range": {"from", "to"}}``.
    """
    report_day = target_date or _today()
    entries_day = report_day - timedelta(days=1)
    range_from = _utc_midnight(entries_day)
    range_to = _utc_midnight(report_day)

    entries = search_ledger(
        conn, project=project, since=range_from, until=range_to, limit=500
    )

    lines = [f"# Daily report — {report_day.isoformat()}"]
    lines += _metadata_block(range_from=range_from, range_to=range_to, project=project)

    citations: list[int] = []
    if not entries:
        lines.append("_No ledger activity for the prior day._")
    else:
        by_project: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for entry in entries:
            by_project[entry["project"]][entry.get("scope") or "(no scope)"].append(entry)

        for proj_name in sorted(by_project):
            lines += ["", f"## {proj_name}"]
            for scope_name in sorted(by_project[proj_name]):
                lines += ["", f"### {scope_name}"]
                for entry in by_project[proj_name][scope_name]:
                    lines.append(_citation_line(entry))
                    citations.append(entry["id"])

    meetings: list[dict] = []
    try:
        from ..webex_store import list_meetings

        today_str = report_day.isoformat()
        meetings = [
            m for m in list_meetings(conn) if str(m.get("start") or "").startswith(today_str)
        ]
    except Exception:  # noqa: BLE001
        meetings = []

    if meetings:
        lines += ["", "## Today's meetings", ""]
        for meeting in meetings:
            lines.append(f"- {meeting.get('start', '')} {meeting.get('title', 'Meeting')}")

    top_todos: list = []
    try:
        from sb_todos import handlers as todo_handlers
        from sb_todos.config import settings as todo_settings
        from sb_todos.db import connect as connect_todos

        todos_conn = connect_todos(todo_settings.db_path)
        try:
            top_todos = todo_handlers.list_todos(todos_conn, status="open", limit=5)
        finally:
            todos_conn.close()
    except Exception:  # noqa: BLE001
        top_todos = []

    if top_todos:
        lines += ["", "## Top open todos", ""]
        for todo in top_todos:
            lines.append(f"- {todo.title} (priority {todo.priority})")

    thread_lines, thread_citations = _open_threads_section(conn, project=project)
    lines += thread_lines
    citations.extend(thread_citations)

    markdown = "\n".join(lines) + "\n"
    return {
        "markdown": markdown,
        "citations": citations,
        "range": {"from": range_from, "to": range_to},
    }


# ---------------------------------------------------------------------------
# weekly
# ---------------------------------------------------------------------------


def weekly(
    conn: sqlite3.Connection,
    *,
    week_end: Optional[date] = None,
    project: Optional[str] = None,
) -> dict:
    """7-day rolling window ending on *week_end* (default today, inclusive).

    Verb-frequency summary, top referenced tickets/links, and a per-day
    digest. Returns ``{"markdown", "citations", "range": {"from", "to"}}``.
    """
    end_day = week_end or _today()
    start_day = end_day - timedelta(days=6)
    range_from = _utc_midnight(start_day)
    range_to = _utc_midnight(end_day + timedelta(days=1))

    entries = search_ledger(
        conn, project=project, since=range_from, until=range_to, limit=1000
    )

    lines = [f"# Weekly report — {start_day.isoformat()} to {end_day.isoformat()}"]
    lines += _metadata_block(range_from=range_from, range_to=range_to, project=project)

    citations: list[int] = []
    if not entries:
        lines.append("_No ledger activity in this window._")
        markdown = "\n".join(lines) + "\n"
        return {
            "markdown": markdown,
            "citations": citations,
            "range": {"from": range_from, "to": range_to},
        }

    verb_counts = Counter(entry.get("action_verb", "Note") for entry in entries)
    lines += ["", "## Verb frequency", ""]
    for verb, count in verb_counts.most_common():
        lines.append(f"- **{verb}**: {count}")

    ref_counts: Counter[str] = Counter()
    for entry in entries:
        for ref in entry.get("refs") or []:
            if isinstance(ref, dict) and ref.get("value"):
                ref_counts[f"{ref.get('kind', 'ref')}:{ref['value']}"] += 1
    if ref_counts:
        lines += ["", "## Top references", ""]
        for ref_key, count in ref_counts.most_common(10):
            lines.append(f"- `{ref_key}`: {count}")

    by_day: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        by_day[_entry_date(entry)].append(entry)

    lines += ["", "## Daily digest"]
    for day_str in sorted(by_day, reverse=True):
        lines += ["", f"### {day_str}"]
        for entry in by_day[day_str]:
            lines.append(_citation_line(entry))
            citations.append(entry["id"])

    thread_lines, thread_citations = _open_threads_section(conn, project=project)
    lines += thread_lines
    citations.extend(thread_citations)

    markdown = "\n".join(lines) + "\n"
    return {
        "markdown": markdown,
        "citations": citations,
        "range": {"from": range_from, "to": range_to},
    }


# ---------------------------------------------------------------------------
# monthly
# ---------------------------------------------------------------------------


def _month_bounds(month_str: str) -> tuple[date, date]:
    year, month = (int(part) for part in month_str.split("-", 1))
    start = date(year, month, 1)
    if month == 12:
        end_exclusive = date(year + 1, 1, 1)
    else:
        end_exclusive = date(year, month + 1, 1)
    end_inclusive = end_exclusive - timedelta(days=1)
    return start, end_inclusive


def monthly(
    conn: sqlite3.Connection,
    *,
    month: Optional[str] = None,
    project: Optional[str] = None,
) -> dict:
    """Rollup of ``month`` (``"YYYY-MM"``, default current month) with
    sub-headings per calendar week. Returns
    ``{"markdown", "citations", "range": {"from", "to"}}``.
    """
    month_str = month or _today().strftime("%Y-%m")
    start_day, end_day = _month_bounds(month_str)
    range_from = _utc_midnight(start_day)
    range_to = _utc_midnight(end_day + timedelta(days=1))

    entries = search_ledger(
        conn, project=project, since=range_from, until=range_to, limit=5000
    )

    lines = [f"# Monthly report — {month_str}"]
    lines += _metadata_block(range_from=range_from, range_to=range_to, project=project)

    citations: list[int] = []
    if not entries:
        lines.append("_No ledger activity this month._")
        markdown = "\n".join(lines) + "\n"
        return {
            "markdown": markdown,
            "citations": citations,
            "range": {"from": range_from, "to": range_to},
        }

    by_week: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for entry in entries:
        day_str = _entry_date(entry)
        try:
            entry_date = date.fromisoformat(day_str)
        except ValueError:
            continue
        iso_year, iso_week, _ = entry_date.isocalendar()
        by_week[(iso_year, iso_week)].append(entry)

    for (iso_year, iso_week) in sorted(by_week):
        week_entries = by_week[(iso_year, iso_week)]
        first_day = min(_entry_date(e) for e in week_entries)
        last_day = max(_entry_date(e) for e in week_entries)
        lines += ["", f"## Week {iso_week} ({first_day} to {last_day})", ""]
        for entry in sorted(week_entries, key=lambda e: e.get("ts", "")):
            lines.append(_citation_line(entry))
            citations.append(entry["id"])

    thread_lines, thread_citations = _open_threads_section(conn, project=project)
    lines += thread_lines
    citations.extend(thread_citations)

    markdown = "\n".join(lines) + "\n"
    return {
        "markdown": markdown,
        "citations": citations,
        "range": {"from": range_from, "to": range_to},
    }


# ---------------------------------------------------------------------------
# query (ad-hoc, LLM-optional)
# ---------------------------------------------------------------------------

_LEDGER_CITATION_RE = None  # set lazily to avoid import cost at module load


def _citation_re():
    global _LEDGER_CITATION_RE
    if _LEDGER_CITATION_RE is None:
        import re

        _LEDGER_CITATION_RE = re.compile(r"\[ledger:(\d+)\]")
    return _LEDGER_CITATION_RE


def _deterministic_query_fallback(entries: list[dict], q: str) -> dict:
    lines = [f"# Query — {q!r}", "", "## Matching ledger entries", ""]
    citations: list[int] = []
    if not entries:
        lines.append("_No matching ledger entries._")
    else:
        for entry in entries:
            lines.append(_citation_line(entry))
            citations.append(entry["id"])
    markdown = "\n".join(lines) + "\n"
    return {"markdown": markdown, "citations": citations, "mode": "fallback"}


def query(
    conn: sqlite3.Connection,
    *,
    q: str,
    project: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    llm_narrate: bool = True,
) -> dict:
    """Ad-hoc "what did I do about X" query over the ledger.

    Retrieves hits via ``search_ledger``. When ``llm_narrate`` is True and
    the LLM backend is available, asks it to narrate the hits into a
    coherent paragraph citing ``[ledger:<id>]``; any hallucinated or missing
    citation set falls back to the deterministic grouped list, exactly like
    every other report in this module.
    """
    entries = search_ledger(conn, q=q, project=project, since=since, until=until, limit=100)

    if not llm_narrate or not entries:
        return _deterministic_query_fallback(entries, q)

    from .. import llm as llm_mod
    from ..config import settings

    context = "\n".join(
        f"[ledger:{entry['id']}] {entry.get('action_verb', 'Note')} {entry.get('summary', '')}"
        for entry in entries
    )
    prompt = (
        f"Answer the question using only LOCAL_CONTEXT below. Every factual "
        f"sentence must end with an exact [ledger:<id>] citation copied from "
        f"context. Only use ids that appear below. Never invent citations.\n\n"
        f"QUESTION\n{q}\nEND_QUESTION\n\nLOCAL_CONTEXT\n{context}\nEND_LOCAL_CONTEXT"
    )

    try:
        narrated = llm_mod.complete(prompt, model=settings.llm_model).strip()
    except llm_mod.LLMUnavailable:
        return _deterministic_query_fallback(entries, q)

    allowed_ids = {entry["id"] for entry in entries}
    cited_ids = {int(match) for match in _citation_re().findall(narrated)}
    if not narrated or not cited_ids or not cited_ids <= allowed_ids:
        return _deterministic_query_fallback(entries, q)

    markdown = f"# Query — {q!r}\n\n{narrated}\n"
    return {"markdown": markdown, "citations": sorted(cited_ids), "mode": "llm"}
