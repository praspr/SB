"""Daily plan tools. Wrap and standup stay unregistered until their own steps."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from fastmcp import FastMCP

from . import goals as goals_mod
from .ranker import rank_todos
from .store import daily as daily_store
from .store import signals as signal_store

mcp = FastMCP("sb-plan")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _get_conn():
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


def _get_todos_conn():
    """Open a fresh todos connection. Callers must close it."""
    from sb_todos.config import settings as todo_settings
    from sb_todos.db import connect as connect_todos

    return connect_todos(todo_settings.db_path)


def _today() -> str:
    return date.today().isoformat()


def _require_date(value: Optional[str]) -> str:
    date_str = value or _today()
    if not _DATE_RE.match(date_str):
        raise ValueError("date must be YYYY-MM-DD")
    try:
        date.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD") from exc
    return date_str


def _roots() -> list[str]:
    from .config import settings

    if settings.roots_detailed:
        return [item["path"] for item in settings.roots_detailed if item.get("path")]
    return list(settings.roots)


def _load_goals(active_only: bool = True) -> dict:
    from .config import settings

    return goals_mod.load_goals(settings.goals_path, active_only=active_only)


def _render_plan(date_str: str, ranked: list[dict], signals: list) -> tuple[str, dict]:
    lines = [f"# Plan {date_str}", "", "## Must-dos", ""]
    if ranked:
        for index, item in enumerate(ranked, start=1):
            lines.append(
                f"{index}. {item.get('title', '(untitled)')} "
                f"— {item['rationale']} (score {item['score']})"
            )
    else:
        lines.append("_No open todos._")

    signal_ids: list[int] = []
    if signals:
        lines += ["", "## Evidence", ""]
        for sig in signals:
            signal_ids.append(sig.id)
            lines.append(f"- [signal:{sig.id}] {sig.title}")

    plan_data = {
        "ranked": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "score": item["score"],
                "rationale": item["rationale"],
            }
            for item in ranked
        ],
        "signal_ids": signal_ids,
    }
    return "\n".join(lines) + "\n", plan_data


@mcp.tool()
def whoami() -> dict:
    """Return the configured identity. Never returns secrets."""
    from .config import settings

    return {"name": settings.identity_name, "email": settings.identity_email}


@mcp.tool()
def get_roots() -> dict:
    """Return configured project roots, including labels when present."""
    from .config import settings

    if settings.roots_detailed:
        return {"roots": list(settings.roots_detailed)}
    return {"roots": [{"path": path} for path in settings.roots]}


@mcp.tool()
def get_goals(active_only: bool = True) -> dict:
    """Return goals grouped by contractual, quarterly, and weekly."""
    return _load_goals(active_only=active_only)


@mcp.tool()
def plan_day(date: Optional[str] = None, refresh: bool = False) -> dict:
    """Rank open todos into a persisted daily plan. Plan columns do not overwrite wrap."""
    from sb_todos import handlers as todo_handlers

    date_str = _require_date(date)
    conn = _get_conn()
    todos_conn = None
    try:
        existing = daily_store.get_daily(conn, date_str)
        if existing and existing.get("plan_md") and not refresh:
            return {
                "date": date_str,
                "plan_md": existing["plan_md"],
                "plan_data": existing.get("plan_data") or {},
                "cached": True,
            }

        todos_conn = _get_todos_conn()
        open_todos = [
            todo.model_dump()
            for todo in todo_handlers.list_todos(todos_conn, status="open", limit=100)
        ]
        goals = _load_goals(active_only=True)
        signals = signal_store.search_signals(conn, limit=20)
        ranked = rank_todos(open_todos, goals, today=date_str)
        plan_md, plan_data = _render_plan(date_str, ranked, signals)
        daily_store.save_plan(conn, date_str, plan_md, plan_data)
        return {
            "date": date_str,
            "plan_md": plan_md,
            "plan_data": plan_data,
            "cached": False,
        }
    finally:
        if todos_conn is not None:
            todos_conn.close()
        conn.close()


@mcp.tool()
def get_day(date: Optional[str] = None) -> dict:
    """Return the persisted plan and wrap for a date."""
    date_str = _require_date(date)
    conn = _get_conn()
    try:
        payload = daily_store.get_daily(conn, date_str) or {}
    finally:
        conn.close()
    return {
        "date": date_str,
        "plan_md": payload.get("plan_md"),
        "plan_data": payload.get("plan_data"),
        "wrap_md": payload.get("wrap_md"),
        "wrap_data": payload.get("wrap_data"),
    }
