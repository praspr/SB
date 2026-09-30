"""Tests for sb_core.webex_store identity helpers: get_identity/set_identity."""

from __future__ import annotations

from pathlib import Path

from sb_core.store.db import connect
from sb_core.webex_store import get_identity, set_identity


def test_get_identity_returns_none_when_never_captured(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        assert get_identity(conn) is None
    finally:
        conn.close()


def test_set_identity_then_get_identity_round_trips(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        set_identity(conn, "me@example.com", "Me Myself")
        identity = get_identity(conn)
        assert identity is not None
        assert identity["email"] == "me@example.com"
        assert identity["display_name"] == "Me Myself"
        assert identity["cached_at"]
    finally:
        conn.close()


def test_set_identity_replaces_a_prior_identity(tmp_path: Path) -> None:
    conn = connect(tmp_path / "core.db")
    try:
        set_identity(conn, "old@example.com", "Old Name")
        set_identity(conn, "new@example.com", "New Name")
        identity = get_identity(conn)
        assert identity is not None
        assert identity["email"] == "new@example.com"

        rows = conn.execute("SELECT COUNT(*) AS n FROM sb_webex_identity").fetchone()
        assert rows["n"] == 1
    finally:
        conn.close()
