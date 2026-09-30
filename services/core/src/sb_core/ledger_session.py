"""Composite session identity for ledger entries.

Session id shape: ``{ISO-UTC-ts}_{agent}_{project}_{short_hash(dir)}_{short_hash(extras)}``.

Time-bucket fallback: within 30 minutes of the most recent session with the
same ``(agent, project, working_dir)``, reuse that session's id rather than
minting a new one — this keeps a single agentic run's entries grouped even
across many separate tool calls.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

_BUCKET_MINUTES = 30


def short_hash(s: str, n: int = 8) -> str:
    """Deterministic short hex digest of *s*, truncated to *n* characters."""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:n]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_extras(extras: Optional[dict]) -> str:
    return json.dumps(extras or {}, sort_keys=True, separators=(",", ":"))


def derive_session_id(
    *,
    agent: str,
    project: str,
    working_dir: Optional[str] = None,
    started_at: Optional[datetime] = None,
    extras: Optional[dict] = None,
) -> str:
    """Derive a fresh, deterministic-for-given-inputs composite session id.

    Two calls with the same ``started_at`` (to the second), agent, project,
    working_dir, and extras produce the same id; a different ``started_at``
    always produces a different id (that is the point of the timestamp
    component — freshness, not stability, is the default for a brand-new
    session).
    """
    ts = started_at or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    ts_str = ts.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dir_hash = short_hash(working_dir or "")
    extras_hash = short_hash(_canonical_extras(extras))
    return f"{ts_str}_{agent}_{project}_{dir_hash}_{extras_hash}"


def resolve_session_id(
    conn: sqlite3.Connection,
    *,
    agent: str,
    project: str,
    working_dir: Optional[str],
    extras: Optional[dict],
    explicit: Optional[str],
) -> str:
    """Resolve the session id to use for a new ledger entry.

    Priority:
    1. ``explicit`` if provided (caller already knows the session id).
    2. Reuse of the most recent session for the same ``(agent, project,
       working_dir)`` tuple if it started within the last 30 minutes.
    3. A freshly derived session id, persisted via ``ensure_session_row``.
    """
    if explicit:
        return explicit

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=_BUCKET_MINUTES)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    row = conn.execute(
        """
        SELECT session_id FROM sb_ledger_sessions
        WHERE agent = ? AND project = ? AND working_dir IS ?
          AND started_at >= ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (agent, project, working_dir, cutoff),
    ).fetchone()
    if row is not None:
        return row["session_id"]

    session_id = derive_session_id(
        agent=agent, project=project, working_dir=working_dir, extras=extras
    )
    ensure_session_row(
        conn, session_id, agent=agent, project=project, working_dir=working_dir, extras=extras
    )
    return session_id


def ensure_session_row(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    agent: Optional[str],
    project: Optional[str],
    working_dir: Optional[str],
    extras: Optional[dict],
) -> None:
    """Write-once insert of a session row. INSERT OR IGNORE — never updates."""
    conn.execute(
        """
        INSERT OR IGNORE INTO sb_ledger_sessions
          (session_id, started_at, agent, working_dir, project, extras)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            utc_now_iso(),
            agent,
            working_dir,
            project,
            _canonical_extras(extras),
        ),
    )
    conn.commit()
