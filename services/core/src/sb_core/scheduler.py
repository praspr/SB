"""Scheduled-rituals engine: a small 5-field cron evaluator plus MCP tools
to register, list, delete, and run due schedules.

No external cron dependency: the parser below covers the common subset used
by this feature (``*``, single values, comma lists, ranges, and step
values) which is sufficient for schedules like ``"0 16 * * 5"`` (Fridays at
16:00 local time). All five fields are evaluated in local time, matching
the plist-driven ``run_due_schedules`` caller (``com.praspr.sb-scheduler``).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Callable, Optional

from fastmcp import FastMCP

from .sync_logger import record_scheduler_run, sync_lock

mcp = FastMCP(
    "sb-scheduler",
    instructions=(
        "Scheduled ritual runner. run_due_schedules is safe to call repeatedly "
        "(idempotent per cron-minute); it only runs a schedule once per fire."
    ),
)

# Search window when looking backward for the most recent cron-matching
# minute. Eight days comfortably covers weekly schedules with margin.
_LOOKBACK_MINUTES = 8 * 24 * 60


def _get_conn() -> sqlite3.Connection:
    from .config import settings
    from .store.db import connect

    return connect(settings.db_path)


def _now_local() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


# ---------------------------------------------------------------------------
# Minimal 5-field cron parser: minute hour dom month dow
# ---------------------------------------------------------------------------


def _parse_field(field: str, low: int, high: int) -> set[int]:
    if field == "*":
        return set(range(low, high + 1))
    values: set[int] = set()
    for part in field.split(","):
        step = 1
        base = part
        if "/" in part:
            base, step_str = part.split("/", 1)
            try:
                step = int(step_str)
            except ValueError as exc:
                raise ValueError(f"bad cron step in field {field!r}") from exc
            if step <= 0:
                raise ValueError(f"bad cron step in field {field!r}")
        try:
            if base == "*":
                rng = range(low, high + 1)
            elif "-" in base:
                start_str, end_str = base.split("-", 1)
                rng = range(int(start_str), int(end_str) + 1)
            else:
                rng = range(int(base), int(base) + 1)
        except ValueError as exc:
            raise ValueError(f"bad cron field {field!r}") from exc
        # Fail loudly on out-of-range values instead of silently yielding an
        # empty set (which would make a typo'd schedule a silent no-op).
        for v in rng:
            if not (low <= v <= high):
                raise ValueError(
                    f"cron value {v} out of range [{low},{high}] in field {field!r}"
                )
        values.update(v for v in rng if (v - low) % step == 0)
    return values


def parse_cron(cron: str) -> dict[str, set[int]]:
    """Parse a 5-field crontab string into per-field allowed-value sets.

    Raises ``ValueError`` for anything that isn't exactly 5 whitespace-
    separated fields.
    """
    fields = cron.split()
    if len(fields) != 5:
        raise ValueError(f"cron must have 5 fields, got {cron!r}")
    minute, hour, dom, month, dow = fields
    # dow accepts 0-7 where both 0 and 7 mean Sunday (standard cron); 7 is
    # normalized to 0 so matching stays in the 0-6 space.
    dow_values = _parse_field(dow, 0, 7)
    if 7 in dow_values:
        dow_values = (dow_values - {7}) | {0}
    return {
        "minute": _parse_field(minute, 0, 59),
        "hour": _parse_field(hour, 0, 23),
        "dom": _parse_field(dom, 1, 31),
        "month": _parse_field(month, 1, 12),
        "dow": dow_values,
    }


def cron_matches(cron: str, when: datetime) -> bool:
    """True if *when* (local time) matches the 5-field crontab *cron*.

    ``dow`` uses cron convention: 0 = Sunday .. 6 = Saturday. Python's
    ``weekday()`` is 0 = Monday .. 6 = Sunday, so it is remapped here.
    """
    parsed = parse_cron(cron)
    cron_dow = (when.weekday() + 1) % 7  # Python Mon=0..Sun=6 -> cron Sun=0..Sat=6
    return (
        when.minute in parsed["minute"]
        and when.hour in parsed["hour"]
        and when.day in parsed["dom"]
        and when.month in parsed["month"]
        and cron_dow in parsed["dow"]
    )


def last_scheduled_at(
    cron: str, now: datetime, *, lookback_minutes: int = _LOOKBACK_MINUTES
) -> Optional[datetime]:
    """Return the most recent minute at or before *now* that matches *cron*,
    searching backward up to *lookback_minutes*. None if no match is found
    in that window (a misconfigured or impossible cron expression).

    DST note: *now* and the walked candidates are naive local time. Around a
    DST transition the local wall-clock minute a schedule fires at is matched
    normally, but duplicate firing is prevented by ``run_due_schedules``, which
    compares the matched ``fire_at`` against the stored ``last_run_at`` and only
    runs when ``fire_at > last_run_at``. So even if a local minute recurs
    (fall-back) the ritual still runs at most once per stored run marker.
    """
    candidate = now
    for _ in range(lookback_minutes + 1):
        if cron_matches(cron, candidate):
            return candidate
        candidate -= timedelta(minutes=1)
    return None


# ---------------------------------------------------------------------------
# Ritual dispatch
# ---------------------------------------------------------------------------


def _ritual_dispatch() -> dict[str, Callable]:
    """Lazily build the name -> callable map to avoid import cycles at
    module load time (ritual_tools/reports_tools both mount on the parent)."""
    from . import ritual_tools
    from .reports import templates as report_templates
    from .store.db import connect as core_connect
    from .config import settings

    def _wrap_day(**kwargs) -> dict:
        return ritual_tools.wrap_day(**kwargs)

    def _standup(**kwargs) -> dict:
        return ritual_tools.standup(**kwargs)

    def _plan_day(**kwargs) -> dict:
        return ritual_tools.plan_day(**kwargs)

    def _report_daily(**kwargs) -> dict:
        conn = core_connect(settings.db_path)
        try:
            from datetime import date as date_cls

            target_date = kwargs.pop("date", None)
            if target_date:
                target_date = date_cls.fromisoformat(target_date)
            return report_templates.daily(conn, target_date=target_date, **kwargs)
        finally:
            conn.close()

    def _report_weekly(**kwargs) -> dict:
        conn = core_connect(settings.db_path)
        try:
            from datetime import date as date_cls

            week_end = kwargs.pop("week_end", None)
            if week_end:
                week_end = date_cls.fromisoformat(week_end)
            return report_templates.weekly(conn, week_end=week_end, **kwargs)
        finally:
            conn.close()

    def _report_monthly(**kwargs) -> dict:
        conn = core_connect(settings.db_path)
        try:
            return report_templates.monthly(conn, **kwargs)
        finally:
            conn.close()

    def _sync_jira(**_kwargs) -> dict:
        from sb_jira.mcp_tools import sync_jira

        result = sync_jira()
        if result.get("errors"):
            raise RuntimeError("; ".join(result["errors"]))
        return result

    def _sync_webex(**_kwargs) -> dict:
        from .webex_tools import sync_webex

        result = sync_webex()
        if result.get("errors"):
            raise RuntimeError("; ".join(result["errors"]))
        return result

    return {
        "wrap_day": _wrap_day,
        "standup": _standup,
        "plan_day": _plan_day,
        "report_daily": _report_daily,
        "report_weekly": _report_weekly,
        "report_monthly": _report_monthly,
        "sync_jira": _sync_jira,
        "sync_webex": _sync_webex,
    }


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
def add_scheduled_ritual(
    name: str,
    ritual: str,
    cron: str,
    args: Optional[dict] = None,
    enabled: bool = True,
    target_dir: Optional[str] = None,
) -> dict:
    """Register a scheduled ritual. ``ritual`` must be one of: wrap_day,
    standup, plan_day, report_daily, report_weekly, report_monthly, sync_jira,
    sync_webex. ``cron`` is a 5-field crontab string evaluated in local time."""
    if ritual not in _ritual_dispatch():
        raise ValueError(f"unknown ritual: {ritual!r}")
    parse_cron(cron)  # validate eagerly; raises ValueError on bad input

    conn = _get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO sb_scheduled_rituals (name, ritual, args_json, cron, target_dir, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                ritual,
                json.dumps(args or {}),
                cron,
                target_dir,
                1 if enabled else 0,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sb_scheduled_rituals WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_schedule(row)
    finally:
        conn.close()


def ensure_default_sync_schedules() -> None:
    """Install safe pull-only defaults once, preserving user-edited schedules."""
    defaults = (
        ("JIRA hourly sync", "sync_jira", "0 * * * *"),
        ("Webex 15-minute sync", "sync_webex", "*/15 * * * *"),
    )
    conn = _get_conn()
    try:
        for name, ritual, cron in defaults:
            conn.execute(
                """
                INSERT INTO sb_scheduled_rituals
                  (name, ritual, args_json, cron, enabled)
                SELECT ?, ?, '{}', ?, 1
                WHERE NOT EXISTS (
                  SELECT 1 FROM sb_scheduled_rituals WHERE name = ?
                )
                """,
                (name, ritual, cron, name),
            )
        conn.commit()
    finally:
        conn.close()


@mcp.tool()
def list_scheduled_rituals() -> list[dict]:
    """List every scheduled ritual (enabled and disabled)."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM sb_scheduled_rituals ORDER BY id").fetchall()
        return [_row_to_schedule(row) for row in rows]
    finally:
        conn.close()


@mcp.tool()
def delete_scheduled_ritual(id: int) -> dict:
    """Delete a scheduled ritual by id. Schedules are metadata, not the
    append-only ledger, so deletion is allowed here."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM sb_scheduled_rituals WHERE id = ?", (id,))
        conn.commit()
        return {"deleted": True, "id": id}
    finally:
        conn.close()


@mcp.tool()
def run_due_schedules() -> dict:
    """Evaluate every enabled schedule's cron against now and run any whose
    most recent matching minute is newer than its last run. Updates
    ``last_run_at``/``last_status`` per schedule. Safe to call repeatedly --
    a schedule only runs once per matching minute."""
    with sync_lock("scheduler_tick") as acquired:
        if not acquired:
            return {"status": "already_running", "outcomes": {}}

        conn = _get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM sb_scheduled_rituals WHERE enabled = 1"
            ).fetchall()
            schedules = [_row_to_schedule(row) for row in rows]
        finally:
            conn.close()

        dispatch = _ritual_dispatch()
        now = _now_local()
        outcomes: dict[str, dict] = {}

        for schedule in schedules:
            fire_at = last_scheduled_at(schedule["cron"], now)
            if fire_at is None:
                outcomes[schedule["name"]] = {"ran": False, "reason": "cron never matches"}
                continue

            last_run_at = schedule.get("last_run_at")
            already_ran = False
            if last_run_at:
                try:
                    last_run_dt = datetime.fromisoformat(last_run_at)
                    already_ran = fire_at <= last_run_dt
                except ValueError:
                    already_ran = False

            if already_ran:
                outcomes[schedule["name"]] = {"ran": False, "reason": "not due"}
                continue

            func = dispatch.get(schedule["ritual"])
            status = "ok"
            error = None
            if func is None:
                status = "error"
                error = f"unknown ritual: {schedule['ritual']!r}"
            else:
                try:
                    func(**schedule["args"])
                except Exception as exc:  # noqa: BLE001
                    status = "error"
                    error = str(exc)

            run_conn = _get_conn()
            try:
                run_conn.execute(
                    "UPDATE sb_scheduled_rituals SET last_run_at = ?, last_status = ? WHERE id = ?",
                    (now.isoformat(), status, schedule["id"]),
                )
                run_conn.commit()
            finally:
                run_conn.close()

            outcomes[schedule["name"]] = {"ran": True, "status": status, "error": error}

        record_scheduler_run(outcomes)
        return {"outcomes": outcomes}


def _row_to_schedule(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["args"] = json.loads(d.pop("args_json") or "{}")
    except json.JSONDecodeError:
        d["args"] = {}
    d["enabled"] = bool(d["enabled"])
    return d
