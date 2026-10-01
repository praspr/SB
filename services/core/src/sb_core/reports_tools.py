"""MCP tools: report_daily, report_weekly, report_monthly, report_query.

Follows the ``sync_tools.py`` shape: every tool opens a fresh connection via
a module-level, test-monkeypatchable ``_get_conn()`` and closes it before
returning. Mounted into the main ``sb`` FastMCP in ``mcp_app.py``.

Date parsing never raises: a malformed ``date``/``week_end``/``month``
argument returns ``{"error": "..."}`` instead.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Optional

from fastmcp import FastMCP

from .reports import templates
from .reports.perf_checkin import perf_checkin as _perf_checkin

mcp = FastMCP(
    "sb-reports",
    instructions=(
        "Read-only ledger reports. Every report is deterministic by default; "
        "report_query may narrate with an LLM but always falls back to a "
        "citation-only listing when the backend is unavailable or hallucinates."
    ),
)


def _get_conn() -> sqlite3.Connection:
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


def _parse_date(value: Optional[str]) -> tuple[Optional[date], Optional[str]]:
    """Return (parsed_date_or_None, error_or_None)."""
    if value is None:
        return None, None
    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, f"invalid date {value!r}: expected YYYY-MM-DD"


def _parse_month(value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if value is None:
        return None, None
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError:
        return None, f"invalid month {value!r}: expected YYYY-MM"
    return value, None


@mcp.tool()
def report_daily(date: Optional[str] = None, project: Optional[str] = None) -> dict:
    """Daily report FOR *date* (default today): yesterday's ledger activity
    grouped by project + scope, today's meetings, top open todos, and open
    threads. ``date`` is ``YYYY-MM-DD``."""
    target_date, error = _parse_date(date)
    if error:
        return {"error": error}
    conn = _get_conn()
    try:
        return templates.daily(conn, target_date=target_date, project=project)
    finally:
        conn.close()


@mcp.tool()
def report_weekly(week_end: Optional[str] = None, project: Optional[str] = None) -> dict:
    """7-day rolling report ending on *week_end* (default today, inclusive).
    ``week_end`` is ``YYYY-MM-DD``."""
    end_date, error = _parse_date(week_end)
    if error:
        return {"error": error}
    conn = _get_conn()
    try:
        return templates.weekly(conn, week_end=end_date, project=project)
    finally:
        conn.close()


@mcp.tool()
def report_monthly(month: Optional[str] = None, project: Optional[str] = None) -> dict:
    """Monthly rollup for *month* (default current). ``month`` is ``YYYY-MM``."""
    month_str, error = _parse_month(month)
    if error:
        return {"error": error}
    conn = _get_conn()
    try:
        return templates.monthly(conn, month=month_str, project=project)
    finally:
        conn.close()


@mcp.tool()
def report_query(
    q: str,
    project: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> dict:
    """Ad-hoc "what did I do about X" query over the ledger. Narrates with an
    LLM when available; always falls back to a citation-only listing."""
    conn = _get_conn()
    try:
        return templates.query(conn, q=q, project=project, since=since, until=until)
    finally:
        conn.close()


@mcp.tool()
def report_perf_checkin(shape: str = "full", voice: str = "first-person") -> dict:
    """Draft a Cisco weekly check-in from ciq CHANGELOG for the previous week.

    Evidence is read exclusively from ``~/Documents/code_home/ciq/CHANGELOG.md``
    (override via ``SB_PERF_CHECKIN_CHANGELOG_PATH``) -- never sb's own
    ledger or CHANGELOG.md. Applies the cisco-iq-performance-checkin skill's
    rules via LLM narration, with a deterministic evidence dump as fallback.

    shape: 'full' (default) or 'one-improvement'.
    voice: 'first-person' (default) or 'third-person'.
    """
    if shape not in ("full", "one-improvement"):
        return {"error": f"shape must be 'full' or 'one-improvement'; got {shape!r}"}
    if voice not in ("first-person", "third-person"):
        return {"error": f"voice must be 'first-person' or 'third-person'; got {voice!r}"}
    return _perf_checkin(shape=shape, voice=voice)
