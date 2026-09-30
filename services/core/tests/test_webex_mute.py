"""Tests for webex_mute.py: mute/unmute/list_muted_spaces MCP tools."""

from __future__ import annotations

from pathlib import Path

import sb_core.webex_mute as wm
from sb_core.store.db import connect


def _seed_space(conn, space_id: str, name: str) -> None:
    conn.execute(
        "INSERT INTO sb_webex_spaces (id, name, synced_at) VALUES (?, ?, ?)",
        (space_id, name, "2026-09-30T00:00:00Z"),
    )
    conn.commit()


def _patch_conn(monkeypatch, db_path: Path) -> None:
    monkeypatch.setattr(wm, "_get_conn", lambda: connect(db_path))


def test_mute_space_sets_flag(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    conn = connect(db_path)
    try:
        _seed_space(conn, "space-1", "Team Room")
    finally:
        conn.close()

    result = wm.mute_space("space-1")
    assert result["muted"] is True
    assert result["found"] is True


def test_unmute_space_clears_flag(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    conn = connect(db_path)
    try:
        _seed_space(conn, "space-1", "Team Room")
    finally:
        conn.close()

    wm.mute_space("space-1")
    result = wm.unmute_space("space-1")
    assert result["muted"] is False


def test_mute_space_not_found_reports_found_false(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    result = wm.mute_space("missing-space")
    assert result["found"] is False
    assert result["muted"] is True


def test_list_muted_spaces_returns_only_muted(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    conn = connect(db_path)
    try:
        _seed_space(conn, "space-1", "Muted Room")
        _seed_space(conn, "space-2", "Loud Room")
    finally:
        conn.close()

    wm.mute_space("space-1")
    muted = wm.list_muted_spaces()
    assert len(muted) == 1
    assert muted[0]["id"] == "space-1"
    assert muted[0]["muted"] is True
