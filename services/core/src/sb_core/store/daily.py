"""Persistence helpers for daily plan/wrap entries and CHANGELOG proposals.

- ``sb_daily`` stores plan and wrap in *separate* columns (``plan_md`` /
  ``plan_data`` and ``wrap_md`` / ``wrap_data``) so a plan write never clobbers a
  wrap write and vice-versa.  ``*_data`` columns hold JSON.  A legacy ``payload``
  JSON column is still read as a fallback for older rows.
- ``sb_proposals`` holds propose-don't-act CHANGELOG suggestions.  ``kind`` is
  exposed as ``type``; the markdown to append lives in the ``body`` column and is
  exposed as ``payload``.  Status transitions are guarded (conditional SQL).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _loads(raw) -> Optional[dict]:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Daily plan/wrap payloads (column-specific to avoid lost updates)
# ---------------------------------------------------------------------------


def get_daily(conn: sqlite3.Connection, date: str) -> Optional[dict]:
    """Return the plan/wrap for *date*, or None if the row is absent.

    Reconstructs the dict from dedicated columns; falls back to the legacy
    ``payload`` JSON blob for rows written before the column split.
    """
    row = conn.execute("SELECT * FROM sb_daily WHERE date = ?", (date,)).fetchone()
    if row is None:
        return None
    d = dict(row)

    legacy = _loads(d.get("payload")) or {}
    result = dict(legacy)
    if d.get("plan_md") is not None:
        result["plan_md"] = d["plan_md"]
    if d.get("plan_data") is not None:
        result["plan_data"] = _loads(d.get("plan_data")) or {}
    if d.get("wrap_md") is not None:
        result["wrap_md"] = d["wrap_md"]
    if d.get("wrap_data") is not None:
        result["wrap_data"] = _loads(d.get("wrap_data")) or {}
    return result


def _upsert_plan(
    conn: sqlite3.Connection, date: str, plan_md: str, plan_data: dict
) -> None:
    conn.execute(
        """
        INSERT INTO sb_daily (date, plan_md, plan_data)
        VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
          plan_md = excluded.plan_md,
          plan_data = excluded.plan_data
        """,
        (date, plan_md, json.dumps(plan_data)),
    )


def _upsert_wrap(
    conn: sqlite3.Connection, date: str, wrap_md: str, wrap_data: dict
) -> None:
    conn.execute(
        """
        INSERT INTO sb_daily (date, wrap_md, wrap_data)
        VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
          wrap_md = excluded.wrap_md,
          wrap_data = excluded.wrap_data
        """,
        (date, wrap_md, json.dumps(wrap_data)),
    )


def save_plan(
    conn: sqlite3.Connection, date: str, plan_md: str, plan_data: dict
) -> None:
    """Upsert only the plan columns for *date* (wrap columns are preserved)."""
    _upsert_plan(conn, date, plan_md, plan_data)
    conn.commit()


def save_wrap(
    conn: sqlite3.Connection, date: str, wrap_md: str, wrap_data: dict
) -> None:
    """Upsert only the wrap columns for *date* (plan columns are preserved)."""
    _upsert_wrap(conn, date, wrap_md, wrap_data)
    conn.commit()


def persist_wrap(
    conn: sqlite3.Connection,
    date: str,
    wrap_md: str,
    wrap_data: dict,
    *,
    proposal: Optional[dict] = None,
) -> Optional[dict]:
    """Persist the wrap and (optionally) queue a proposal in ONE transaction.

    ``proposal`` is a dict of ``create_proposal`` keyword arguments.  If an
    identical pending proposal already exists (same target_path + payload) it is
    reused rather than duplicated.  Returns the proposal dict (new or existing)
    or None when no proposal was requested.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        _upsert_wrap(conn, date, wrap_md, wrap_data)

        result: Optional[dict] = None
        if proposal is not None:
            existing = _find_pending(
                conn,
                target_path=proposal.get("target_path"),
                payload=proposal.get("payload", ""),
            )
            if existing is not None:
                result = existing
            else:
                result = _insert_proposal(conn, **proposal)
    except Exception:
        conn.rollback()
        raise
    conn.commit()
    return result


# ---------------------------------------------------------------------------
# Proposals
# ---------------------------------------------------------------------------


def _row_to_proposal(row: sqlite3.Row) -> dict:
    d = dict(row)
    refs = _loads(d.get("signal_refs")) or []
    return {
        "id": d["id"],
        "type": d["kind"],
        "title": d["title"],
        "target_path": d.get("target_path"),
        "payload": d.get("body") or "",
        "status": d["status"],
        "signal_refs": refs,
        "created_at": d["created_at"],
        "updated_at": d.get("updated_at"),
    }


def _insert_proposal(
    conn: sqlite3.Connection,
    *,
    kind: str,
    title: str,
    target_path: Optional[str] = None,
    payload: str = "",
    signal_refs: Optional[list] = None,
) -> dict:
    now = _now_utc()
    cursor = conn.execute(
        """
        INSERT INTO sb_proposals
          (kind, title, body, status, signal_refs, target_path, created_at, updated_at)
        VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            kind,
            title,
            payload,
            json.dumps(signal_refs or []),
            target_path,
            now,
            now,
        ),
    )
    row = conn.execute(
        "SELECT * FROM sb_proposals WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_proposal(row)


def create_proposal(
    conn: sqlite3.Connection,
    *,
    kind: str,
    title: str,
    target_path: Optional[str] = None,
    payload: str = "",
    signal_refs: Optional[list] = None,
) -> dict:
    proposal = _insert_proposal(
        conn,
        kind=kind,
        title=title,
        target_path=target_path,
        payload=payload,
        signal_refs=signal_refs,
    )
    conn.commit()
    return proposal


def get_proposal(conn: sqlite3.Connection, proposal_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM sb_proposals WHERE id = ?", (proposal_id,)
    ).fetchone()
    return _row_to_proposal(row) if row else None


def list_proposals(
    conn: sqlite3.Connection, status: Optional[str] = "pending"
) -> list[dict]:
    if status:
        rows = conn.execute(
            "SELECT * FROM sb_proposals WHERE status = ? ORDER BY id DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sb_proposals ORDER BY id DESC").fetchall()
    return [_row_to_proposal(row) for row in rows]


def _find_pending(
    conn: sqlite3.Connection, *, target_path: Optional[str], payload: str
) -> Optional[dict]:
    row = conn.execute(
        """
        SELECT * FROM sb_proposals
        WHERE status = 'pending' AND target_path IS ? AND body = ?
        ORDER BY id DESC LIMIT 1
        """,
        (target_path, payload),
    ).fetchone()
    return _row_to_proposal(row) if row else None


def find_pending_proposal(
    conn: sqlite3.Connection, *, target_path: Optional[str], payload: str
) -> Optional[dict]:
    """Return an existing pending proposal with the same target/payload, if any."""
    return _find_pending(conn, target_path=target_path, payload=payload)


def transition_proposal(
    conn: sqlite3.Connection,
    proposal_id: int,
    expected_from: str,
    to_status: str,
) -> bool:
    """Conditionally move a proposal from *expected_from* to *to_status*.

    Uses a single conditional UPDATE so only a row currently in *expected_from*
    transitions.  Returns True when exactly one row changed, else False.
    """
    now = _now_utc()
    cursor = conn.execute(
        """
        UPDATE sb_proposals
        SET status = ?, updated_at = ?, decided_at = ?
        WHERE id = ? AND status = ?
        """,
        (to_status, now, now, proposal_id, expected_from),
    )
    conn.commit()
    return cursor.rowcount == 1
