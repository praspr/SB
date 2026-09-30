"""Chief-of-staff ritual tools: context, plan, wrap, standup, proposals.

Mounted into the unified sb FastMCP in ``mcp_app.py``.

Design:
- Every tool opens fresh connections through patchable module-level helpers
  (``_get_conn`` for core.db, ``_get_todos_conn`` for todos.db).
- Ranking is deterministic (see ``ranker``).  Wrap narrative may use the LLM
  but always validates ``[signal:N]`` citations and falls back deterministically
  when the backend is unavailable or hallucinates ids.
- Proposals are *propose-don't-act*.  Only ``approve_proposal`` writes, and only
  a local ``CHANGELOG.md`` under a configured root after strict path safety.
  Nothing here ever writes to Atlassian.
"""

from __future__ import annotations

import os
import re
import sqlite3
import stat
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from . import goals as goals_mod
from . import llm
from .ranker import rank_todos
from .store import daily as daily_store
from .store import signals as signal_store

mcp = FastMCP("sb-ritual")

_CITATION_RE = re.compile(r"\[signal:(\d+)\]")
_MAX_CHANGELOG_PAYLOAD = 20_000  # bytes cap for an appended CHANGELOG entry
_MAX_CHANGELOG_FILE = 1_048_576  # refuse to append into a larger file


# ---------------------------------------------------------------------------
# Patchable helpers (override in tests via monkeypatch)
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


def _get_todos_conn() -> sqlite3.Connection:
    from sb_todos.config import settings as todo_settings
    from sb_todos.db import connect as todos_connect

    return todos_connect(todo_settings.db_path)


def _today() -> str:
    return date.today().isoformat()


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _require_date(date_str: str) -> str:
    if not _DATE_RE.match(date_str):
        raise ValueError("date must be YYYY-MM-DD")
    try:
        date.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD") from exc
    return date_str


def _tz():
    return datetime.now().astimezone().tzinfo


def _local_day_bounds(date_str: str) -> tuple[str, str]:
    """Return the UTC half-open range covering the local calendar day."""
    start_local = datetime.fromisoformat(date_str).replace(tzinfo=_tz())
    end_local = start_local + timedelta(days=1)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    start = start_local.astimezone(timezone.utc).strftime(fmt)
    end = end_local.astimezone(timezone.utc).strftime(fmt)
    return start, end


def _roots() -> list[str]:
    from .config import settings

    if settings.roots_detailed:
        return [r["path"] for r in settings.roots_detailed if r.get("path")]
    return list(settings.roots)


def _load_goals(active_only: bool = True) -> dict:
    from .config import settings

    return goals_mod.load_goals(settings.goals_path, active_only=active_only)


def _llm_complete(prompt: str) -> str:
    return llm.complete(prompt)


# ---------------------------------------------------------------------------
# Context tools
# ---------------------------------------------------------------------------


@mcp.tool()
def whoami() -> dict:
    """Return the configured identity (name/email).  Never returns secrets."""
    from .config import settings

    return {"name": settings.identity_name, "email": settings.identity_email}


@mcp.tool()
def get_roots() -> dict:
    """Return configured project roots, preserving labels/domain when supplied."""
    from .config import settings

    return {"roots": list(settings.roots_detailed)}


@mcp.tool()
def get_goals(active_only: bool = True) -> dict:
    """Return goals grouped by contractual/quarterly/weekly.

    Missing goals file yields an empty structured result (never an error).
    """
    return _load_goals(active_only=active_only)


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def _render_plan(date_str: str, ranked: list[dict], signals: list) -> tuple[str, dict]:
    lines = [f"# Plan {date_str}", "", "## Must-dos", ""]
    if ranked:
        for i, item in enumerate(ranked, start=1):
            lines.append(
                f"{i}. {item.get('title', '(untitled)')} "
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

    plan_md = "\n".join(lines) + "\n"
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
    return plan_md, plan_data


@mcp.tool()
def plan_day(date: Optional[str] = None, refresh: bool = False) -> dict:
    """Build (and persist) an evidence-backed daily plan of ranked must-dos.

    Reads open todos, recent signals, and goals.  Persists one ``sb_daily`` row
    per date.  Returns the persisted entry unchanged when present and not
    ``refresh``.
    """
    from sb_todos import handlers as todo_handlers

    date_str = _require_date(date or _today())
    conn = _get_conn()
    todos_conn = None
    try:
        existing = daily_store.get_daily(conn, date_str)
        if existing and existing.get("plan_md") and not refresh:
            return {
                "date": date_str,
                "plan_md": existing["plan_md"],
                "plan_data": existing.get("plan_data", {}),
                "cached": True,
            }

        todos_conn = _get_todos_conn()
        open_todos = [
            t.model_dump()
            for t in todo_handlers.list_todos(todos_conn, status="open", limit=100)
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
    """Return the persisted plan/wrap for *date* (stable empty shape if absent)."""
    date_str = _require_date(date or _today())
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


# ---------------------------------------------------------------------------
# Standup
# ---------------------------------------------------------------------------


@mcp.tool()
def standup(date: Optional[str] = None) -> dict:
    """Generate 5-8 concise, deterministic standup bullets. No side effects."""
    from sb_todos import handlers as todo_handlers

    date_str = _require_date(date or _today())
    prev = (
        datetime.strptime(date_str, "%Y-%m-%d").date() - timedelta(days=1)
    ).isoformat()
    conn = _get_conn()
    todos_conn = None
    try:
        payload = daily_store.get_daily(conn, date_str) or {}
        previous = daily_store.get_daily(conn, prev) or {}
        todos_conn = _get_todos_conn()
        p1 = todo_handlers.list_todos(todos_conn, status="open", priority=1, limit=100)
        p2 = todo_handlers.list_todos(todos_conn, status="open", priority=2, limit=100)
    finally:
        if todos_conn is not None:
            todos_conn.close()
        conn.close()

    bullets: list[str] = [f"Standup for {date_str}."]

    plan_data = payload.get("plan_data") or {}
    ranked = plan_data.get("ranked") or []
    if ranked:
        top = ranked[0]
        bullets.append(f"Top planned focus: {top.get('title')}.")
        if len(ranked) > 1:
            bullets.append(f"Also planned: {ranked[1].get('title')}.")

    if previous.get("wrap_md"):
        bullets.append("Yesterday's wrap is recorded.")

    if p1:
        bullets.append("P1 in progress: " + ", ".join(t.title for t in p1[:3]) + ".")
    if p2:
        bullets.append("P2 queued: " + ", ".join(t.title for t in p2[:3]) + ".")

    if not p1 and not p2:
        bullets.append("No P1/P2 tasks open.")

    _pad = [
        "Focus is on planned must-dos.",
        "Evidence is tracked via local signals.",
        "Proposals require explicit approval.",
    ]
    while len(bullets) < 5:
        bullets.append(_pad[(len(bullets) - 1) % len(_pad)])

    return {"date": date_str, "bullets": bullets[:8]}


# ---------------------------------------------------------------------------
# Wrap
# ---------------------------------------------------------------------------


def _gather_wrap(conn: sqlite3.Connection, date_str: str) -> list:
    """Return signals that fall in the local calendar day, queried as a UTC range."""
    since, until = _local_day_bounds(date_str)
    return signal_store.search_signals(conn, since=since, until=until, limit=500)


def _fallback_wrap_md(date_str: str, signals: list) -> str:
    lines = [f"# Wrap {date_str}", "", "## Completed / Activity", ""]
    if signals:
        for sig in signals:
            verb = (sig.verb or "").strip()
            prefix = f"{verb.capitalize()}: " if verb else ""
            lines.append(f"- {prefix}{sig.title} [signal:{sig.id}]")
    else:
        lines.append("_No signals recorded for this date._")
    lines += [
        "",
        "## Notes",
        "",
        f"- {len(signals)} signal(s) gathered for {date_str}.",
    ]
    return "\n".join(lines) + "\n"


def _llm_bullets_ok(text: str, gathered_ids: set[int]) -> bool:
    """Every factual bullet must cite only ids from the gathered evidence."""
    if not gathered_ids:
        return False
    bullets = [
        line.strip() for line in text.splitlines() if line.strip().startswith("- ")
    ]
    if not bullets:
        return False
    for bullet in bullets:
        ids = {int(n) for n in _CITATION_RE.findall(bullet)}
        if not ids or not ids <= gathered_ids:
            return False
    return True


@mcp.tool()
def wrap_day(
    date: Optional[str] = None, dry_run: bool = True, refresh: bool = False
) -> dict:
    """Produce an evidence-backed day wrap.

    Gathers that date's signals, generates markdown whose factual bullets each
    carry a valid ``[signal:N]`` citation.  When an LLM narrative is available
    its citations are validated; hallucinated ids trigger the deterministic
    fallback.  Persists (and queues a CHANGELOG proposal) only when
    ``dry_run`` is False.
    """
    date_str = _require_date(date or _today())
    conn = _get_conn()
    try:
        existing = daily_store.get_daily(conn, date_str)
        if not dry_run and existing and existing.get("wrap_md") and not refresh:
            return {
                "date": date_str,
                "wrap_md": existing["wrap_md"],
                "wrap_data": existing.get("wrap_data", {}),
                "dry_run": False,
                "persisted": True,
                "cached": True,
                "proposals": [],
            }

        signals = _gather_wrap(conn, date_str)
        gathered_ids = {s.id for s in signals}

        wrap_md = _fallback_wrap_md(date_str, signals)
        used_llm = False
        if signals:
            try:
                evidence = "\n".join(f"[signal:{s.id}] {s.title}" for s in signals)
                prompt = (
                    f"Summarize the work completed on {date_str} as concise bullets. "
                    "Cite each factual bullet with a [signal:N] id from this evidence. "
                    "Only use ids that appear below.\n\n" + evidence
                )
                candidate = _llm_complete(prompt)
                if candidate and _llm_bullets_ok(candidate, gathered_ids):
                    wrap_md = (
                        candidate if candidate.endswith("\n") else candidate + "\n"
                    )
                    used_llm = True
            except llm.LLMUnavailable:
                used_llm = False

        wrap_data = {
            "signal_ids": sorted(gathered_ids),
            "used_llm": used_llm,
        }

        if dry_run:
            return {
                "date": date_str,
                "wrap_md": wrap_md,
                "wrap_data": wrap_data,
                "dry_run": True,
                "persisted": False,
                "proposals": [],
            }

        proposal_arg = None
        roots = _roots()
        if roots and signals:
            target = str(Path(roots[0]).expanduser() / "CHANGELOG.md")
            entry_lines = [f"## {date_str}"]
            for sig in signals:
                entry_lines.append(f"- {sig.title} [signal:{sig.id}]")
            proposal_arg = {
                "kind": "changelog",
                "title": f"CHANGELOG update for {date_str}",
                "target_path": target,
                "payload": "\n".join(entry_lines) + "\n",
                "signal_refs": sorted(gathered_ids),
            }
        proposal = daily_store.persist_wrap(
            conn, date_str, wrap_md, wrap_data, proposal=proposal_arg
        )
        proposals = [proposal] if proposal else []

        return {
            "date": date_str,
            "wrap_md": wrap_md,
            "wrap_data": wrap_data,
            "dry_run": False,
            "persisted": True,
            "proposals": proposals,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Proposals: list / reject / approve
# ---------------------------------------------------------------------------


@mcp.tool()
def list_proposals(status: str = "pending") -> list[dict]:
    """List proposals, filtered by status (default ``pending``)."""
    conn = _get_conn()
    try:
        return daily_store.list_proposals(conn, status=status or None)
    finally:
        conn.close()


@mcp.tool()
def reject_proposal(proposal_id: int) -> dict:
    """Mark a proposal rejected."""
    conn = _get_conn()
    try:
        proposal = daily_store.get_proposal(conn, proposal_id)
        if proposal is None:
            raise ValueError(f"proposal {proposal_id} not found")
        return daily_store.set_proposal_status(conn, proposal_id, "rejected")
    finally:
        conn.close()


def _path_has_symlink(path: Path) -> bool:
    """True when any existing component of *path*, including the leaf, is a symlink."""
    current = Path(path.anchor) if path.is_absolute() else Path()
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _safe_changelog_target(target_path: str, roots: list[str]) -> Path:
    """Resolve *target_path* under a configured root with strict safety.

    The basename must be exactly ``CHANGELOG.md``. Any symlink component is
    rejected, including a symlink that stays inside the root. The resolved path
    must live under a configured root. A missing parent is created only when
    that parent is inside the root and contains no symlink.
    """
    if not roots:
        raise ValueError("no configured roots; refusing to write")

    candidate = Path(target_path).expanduser()
    if candidate.name != "CHANGELOG.md":
        raise ValueError("target filename must be exactly CHANGELOG.md")
    if _path_has_symlink(candidate):
        raise ValueError("changelog path must not contain a symlink")

    resolved = candidate.resolve()
    if resolved.name != "CHANGELOG.md":
        raise ValueError("target filename must be exactly CHANGELOG.md")
    if _path_has_symlink(resolved):
        raise ValueError("changelog path must not contain a symlink")

    for root in roots:
        root_real = Path(root).expanduser().resolve()
        try:
            resolved.relative_to(root_real)
        except ValueError:
            continue
        parent = resolved.parent
        if not parent.exists():
            if _path_has_symlink(parent):
                raise ValueError("changelog path must not contain a symlink")
            try:
                parent.resolve().relative_to(root_real)
            except ValueError as exc:
                raise ValueError(
                    "target does not resolve under any configured root"
                ) from exc
            parent.mkdir(parents=True, exist_ok=True)
        return resolved
    raise ValueError("target does not resolve under any configured root")


@mcp.tool()
def approve_proposal(proposal_id: int) -> dict:
    """Approve and execute a CHANGELOG proposal after strict path safety.

    On success the payload is appended once (idempotently) to the target
    ``CHANGELOG.md`` and the proposal status becomes ``executed``.  This never
    writes to Jira or any remote system.
    """
    conn = _get_conn()
    try:
        proposal = daily_store.get_proposal(conn, proposal_id)
        if proposal is None:
            raise ValueError(f"proposal {proposal_id} not found")
        if proposal["status"] != "pending":
            raise ValueError(f"proposal {proposal_id} is not pending")
        if proposal["type"] != "changelog":
            raise ValueError(f"unsupported proposal type: {proposal['type']!r}")

        payload = proposal["payload"] or ""
        if not isinstance(payload, str) or not payload.strip():
            raise ValueError("proposal payload must be non-empty markdown text")
        if len(payload.encode("utf-8")) > _MAX_CHANGELOG_PAYLOAD:
            raise ValueError("proposal payload exceeds the size cap")

        target = _safe_changelog_target(proposal["target_path"] or "", _roots())

        appended = False
        existing = ""
        if target.exists():
            info = target.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ValueError("changelog path must not contain a symlink")
            if info.st_size > _MAX_CHANGELOG_FILE:
                raise ValueError("changelog exceeds the size cap")
            existing = target.read_text(encoding="utf-8")
        if payload.strip() not in existing:
            data = payload if payload.endswith("\n") else payload + "\n"
            if existing and not existing.endswith("\n"):
                data = "\n" + data
            fd = os.open(
                target,
                os.O_APPEND | os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW,
            )
            try:
                os.write(fd, data.encode("utf-8"))
            finally:
                os.close(fd)
            appended = True

        updated = daily_store.set_proposal_status(conn, proposal_id, "executed")
        result = dict(updated) if updated else {}
        result["appended"] = appended
        return result
    finally:
        conn.close()
