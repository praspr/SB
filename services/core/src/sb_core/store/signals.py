"""Signal upsert and parameterized search for core.db."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from typing import Optional

from .models import Signal

# ---------------------------------------------------------------------------
# occurred_at normalisation
# ---------------------------------------------------------------------------

_FALLBACK_OCCURRED = "1970-01-01T00:00:00Z"


def normalize_occurred_at(raw: str) -> str:
    """Coerce any reasonable date/datetime string to canonical ``YYYY-MM-DDTHH:MM:SSZ``.

    Accepted inputs (examples):
    * ``"2026-06-15T14:30:00Z"``        – already canonical, returned unchanged
    * ``"2026-06-15T14:30:00+05:30"``   – offset converted to UTC
    * ``"2026-06-15 14:30:00"``         – space-separated, assumed UTC
    * ``"2026-06-15"``                  – date-only, midnight UTC
    * ``""`` / blank                    – returns _FALLBACK_OCCURRED
    """
    raw = (raw or "").strip()
    if not raw:
        return _FALLBACK_OCCURRED

    # Already canonical
    if len(raw) == 20 and raw[10] == "T" and raw.endswith("Z"):
        return raw

    # Replace space separator → T for fromisoformat compatibility
    iso = raw.replace(" ", "T", 1) if " " in raw and "T" not in raw else raw

    # Try full datetime parse (handles +HH:MM offsets, Z suffix, etc.)
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass

    # Try date-only
    try:
        d = date.fromisoformat(raw[:10])
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except ValueError:
        pass

    return _FALLBACK_OCCURRED


# ---------------------------------------------------------------------------
# LIKE escape helper (Issue 5)
# ---------------------------------------------------------------------------


def _like_escape(s: str) -> str:
    """Escape LIKE special characters so a user query is treated as a literal."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ---------------------------------------------------------------------------
# Internal row conversion
# ---------------------------------------------------------------------------


def _row_to_signal(row: sqlite3.Row) -> Signal:
    d = dict(row)
    refs = json.loads(d.get("refs") or "[]")
    return Signal(
        id=d["id"],
        source=d["source"],
        source_id=d["source_id"],
        kind=d["kind"],
        occurred_at=d["occurred_at"],
        title=d["title"],
        body=d.get("body"),
        scope=d.get("scope"),
        verb=d.get("verb"),
        refs=refs,
        raw_ref=d.get("raw_ref"),
        created_at=d["created_at"],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def upsert_signal(
    conn: sqlite3.Connection,
    *,
    source: str,
    source_id: str,
    kind: str,
    occurred_at: str,
    title: str,
    body: Optional[str] = None,
    scope: Optional[str] = None,
    verb: Optional[str] = None,
    refs: Optional[list] = None,
    raw_ref: Optional[str] = None,
) -> Signal:
    """Insert or update a signal keyed on ``(source, source_id)``.

    ``occurred_at`` is normalised to canonical UTC before storage.
    ``created_at`` is set on INSERT only (preserved on UPDATE).
    """
    normalised_at = normalize_occurred_at(occurred_at)
    refs_json = json.dumps(refs or [])
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # canonical UTC

    conn.execute(
        """
        INSERT INTO sb_signals
          (source, source_id, kind, occurred_at, title, body, scope, verb, refs, raw_ref, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source, source_id) DO UPDATE SET
          kind        = excluded.kind,
          occurred_at = excluded.occurred_at,
          title       = excluded.title,
          body        = excluded.body,
          scope       = excluded.scope,
          verb        = excluded.verb,
          refs        = excluded.refs,
          raw_ref     = excluded.raw_ref
        """,
        (
            source,
            source_id,
            kind,
            normalised_at,
            title,
            body,
            scope,
            verb,
            refs_json,
            raw_ref,
            now_utc,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM sb_signals WHERE source = ? AND source_id = ?",
        (source, source_id),
    ).fetchone()
    return _row_to_signal(row)


def search_signals(
    conn: sqlite3.Connection,
    *,
    q: Optional[str] = None,
    source: Optional[str] = None,
    kind: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 100,
) -> list[Signal]:
    """Parameterized signal search with LIKE-escape for ``q``.

    ``since`` is an inclusive lower bound (``occurred_at >= since``); ``until``
    is an *exclusive* upper bound (``occurred_at < until``).  Together they
    express a half-open ``[since, until)`` range — e.g. a single local calendar
    day expressed in UTC.
    """
    clauses: list[str] = []
    params: list[object] = []

    if q:
        escaped = _like_escape(q)
        like = f"%{escaped}%"
        clauses.append("(title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\')")
        params.extend([like, like])

    if source:
        clauses.append("source = ?")
        params.append(source)

    if kind:
        clauses.append("kind = ?")
        params.append(kind)

    if since:
        clauses.append("occurred_at >= ?")
        params.append(since)

    if until:
        clauses.append("occurred_at < ?")
        params.append(until)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    rows = conn.execute(
        f"SELECT * FROM sb_signals {where} ORDER BY occurred_at DESC LIMIT ?",
        params,
    ).fetchall()
    return [_row_to_signal(row) for row in rows]
