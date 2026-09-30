"""Tests for sb_core.ledger_session: derivation determinism and bucket reuse."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sb_core.ledger_session import (
    derive_session_id,
    ensure_session_row,
    resolve_session_id,
    short_hash,
    utc_now_iso,
)
from sb_core.store.db import connect


def test_short_hash_is_deterministic_and_truncated() -> None:
    a = short_hash("/Users/x/project")
    b = short_hash("/Users/x/project")
    assert a == b
    assert len(a) == 8


def test_short_hash_differs_for_different_input() -> None:
    assert short_hash("a") != short_hash("b")


def test_utc_now_iso_shape() -> None:
    value = utc_now_iso()
    assert value.endswith("Z")
    assert "T" in value


def test_derive_session_id_is_deterministic_for_same_timestamp() -> None:
    ts = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
    a = derive_session_id(agent="cursor", project="sb", working_dir="/a", started_at=ts)
    b = derive_session_id(agent="cursor", project="sb", working_dir="/a", started_at=ts)
    assert a == b


def test_derive_session_id_differs_by_agent_project_dir_extras() -> None:
    ts = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
    base = derive_session_id(agent="cursor", project="sb", working_dir="/a", started_at=ts)
    diff_agent = derive_session_id(agent="opencode", project="sb", working_dir="/a", started_at=ts)
    diff_project = derive_session_id(agent="cursor", project="ciq", working_dir="/a", started_at=ts)
    diff_dir = derive_session_id(agent="cursor", project="sb", working_dir="/b", started_at=ts)
    diff_extras = derive_session_id(
        agent="cursor", project="sb", working_dir="/a", started_at=ts, extras={"k": "v"}
    )
    assert len({base, diff_agent, diff_project, diff_dir, diff_extras}) == 5


def test_derive_session_id_differs_by_timestamp() -> None:
    ts1 = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 9, 30, 12, 5, 0, tzinfo=timezone.utc)
    a = derive_session_id(agent="cursor", project="sb", started_at=ts1)
    b = derive_session_id(agent="cursor", project="sb", started_at=ts2)
    assert a != b


def test_resolve_session_id_uses_explicit_when_provided(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        result = resolve_session_id(
            conn,
            agent="cursor",
            project="sb",
            working_dir="/a",
            extras=None,
            explicit="explicit-session-id",
        )
        assert result == "explicit-session-id"
    finally:
        conn.close()


def test_resolve_session_id_derives_fresh_when_no_prior_session(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        result = resolve_session_id(
            conn, agent="cursor", project="sb", working_dir="/a", extras=None, explicit=None
        )
        assert result
        row = conn.execute(
            "SELECT session_id FROM sb_ledger_sessions WHERE session_id = ?", (result,)
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_resolve_session_id_reuses_within_30_minute_bucket(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        ensure_session_row(
            conn,
            "prior-session-id",
            agent="cursor",
            project="sb",
            working_dir="/a",
            extras=None,
        )
        # Force started_at into the recent past directly (ensure_session_row
        # always stamps "now"; overwrite for a controlled bucket test).
        conn.execute(
            "UPDATE sb_ledger_sessions SET started_at = ? WHERE session_id = ?",
            (recent, "prior-session-id"),
        )
        conn.commit()

        result = resolve_session_id(
            conn, agent="cursor", project="sb", working_dir="/a", extras=None, explicit=None
        )
        assert result == "prior-session-id"
    finally:
        conn.close()


def test_resolve_session_id_does_not_reuse_outside_30_minute_bucket(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        stale = (datetime.now(timezone.utc) - timedelta(minutes=45)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        ensure_session_row(
            conn,
            "stale-session-id",
            agent="cursor",
            project="sb",
            working_dir="/a",
            extras=None,
        )
        conn.execute(
            "UPDATE sb_ledger_sessions SET started_at = ? WHERE session_id = ?",
            (stale, "stale-session-id"),
        )
        conn.commit()

        result = resolve_session_id(
            conn, agent="cursor", project="sb", working_dir="/a", extras=None, explicit=None
        )
        assert result != "stale-session-id"
    finally:
        conn.close()


def test_resolve_session_id_isolates_by_tuple(tmp_path: Path) -> None:
    """A recent session for a different (agent, project, working_dir) tuple
    must never be reused."""
    conn = connect(tmp_path / "core.db")
    try:
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        ensure_session_row(
            conn,
            "other-tuple-session",
            agent="opencode",
            project="ciq",
            working_dir="/other",
            extras=None,
        )
        conn.execute(
            "UPDATE sb_ledger_sessions SET started_at = ? WHERE session_id = ?",
            (recent, "other-tuple-session"),
        )
        conn.commit()

        result = resolve_session_id(
            conn, agent="cursor", project="sb", working_dir="/a", extras=None, explicit=None
        )
        assert result != "other-tuple-session"
    finally:
        conn.close()


def test_ensure_session_row_is_write_once(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        ensure_session_row(
            conn, "fixed-id", agent="cursor", project="sb", working_dir="/a", extras=None
        )
        first_started = conn.execute(
            "SELECT started_at FROM sb_ledger_sessions WHERE session_id = ?", ("fixed-id",)
        ).fetchone()["started_at"]

        # Second call must not overwrite started_at (INSERT OR IGNORE).
        ensure_session_row(
            conn, "fixed-id", agent="cursor", project="sb", working_dir="/a", extras=None
        )
        second_started = conn.execute(
            "SELECT started_at FROM sb_ledger_sessions WHERE session_id = ?", ("fixed-id",)
        ).fetchone()["started_at"]
        assert first_started == second_started
    finally:
        conn.close()
