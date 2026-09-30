"""Tests for goals_tools.py: CRUD, alignment scoring, heatmap."""

from __future__ import annotations

import asyncio
from pathlib import Path

import sb_core.goals_tools as gt
from sb_core.store.db import connect
from sb_core.store.ledger import append_ledger


def _patch_conn(monkeypatch, db_path: Path) -> None:
    monkeypatch.setattr(gt, "_get_conn", lambda: connect(db_path))


def test_goals_tools_are_registered_and_mounted() -> None:
    names = {t.name for t in asyncio.run(gt.mcp.list_tools())}
    expected = {
        "list_goals_v2",
        "get_goal_v2",
        "add_goal",
        "update_goal",
        "archive_goal",
        "score_alignment",
        "heatmap_last_week",
    }
    assert expected <= names

    from sb_core.mcp_app import mcp as parent

    mounted = {t.name for t in asyncio.run(parent.list_tools())}
    assert "add_goal" in mounted
    assert "heatmap_last_week" in mounted


def test_add_goal_and_list_goals_v2(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    created = gt.add_goal(tier="quarterly", title="Ship the ledger", keywords=["ledger", "phase"])
    assert created["tier"] == "quarterly"
    assert created["keywords"] == ["ledger", "phase"]
    assert created["status"] == "active"

    goals = gt.list_goals_v2()
    assert len(goals) == 1
    assert goals[0]["title"] == "Ship the ledger"


def test_add_goal_rejects_invalid_tier(tmp_path, monkeypatch) -> None:
    import pytest

    _patch_conn(monkeypatch, tmp_path / "core.db")
    with pytest.raises(ValueError):
        gt.add_goal(tier="yearly", title="bad tier")


def test_list_goals_v2_filters_by_tier_and_status(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    gt.add_goal(tier="weekly", title="Weekly thing")
    gt.add_goal(tier="quarterly", title="Quarterly thing")

    weekly_only = gt.list_goals_v2(tier="weekly")
    assert len(weekly_only) == 1
    assert weekly_only[0]["tier"] == "weekly"

    all_statuses = gt.list_goals_v2(status=None)
    assert len(all_statuses) == 2


def test_get_goal_v2_returns_none_for_missing(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    assert gt.get_goal_v2(999) is None


def test_update_goal_changes_only_provided_fields(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    created = gt.add_goal(tier="weekly", title="Original title", description="orig desc")
    updated = gt.update_goal(created["id"], title="New title")
    assert updated["title"] == "New title"
    assert updated["description"] == "orig desc"
    assert updated["updated_at"] is not None


def test_update_goal_raises_for_missing_id(tmp_path, monkeypatch) -> None:
    import pytest

    _patch_conn(monkeypatch, tmp_path / "core.db")
    with pytest.raises(ValueError):
        gt.update_goal(999, title="nope")


def test_archive_goal_transitions_status_not_delete(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    created = gt.add_goal(tier="weekly", title="To archive")
    archived = gt.archive_goal(created["id"])
    assert archived["status"] == "archived"

    # Row still exists (not deleted), just filtered out of the active list.
    assert gt.get_goal_v2(created["id"]) is not None
    assert gt.list_goals_v2(status="active") == []
    assert len(gt.list_goals_v2(status="archived")) == 1


def test_score_alignment_requires_exactly_one_id(tmp_path, monkeypatch) -> None:
    import pytest

    _patch_conn(monkeypatch, tmp_path / "core.db")
    with pytest.raises(ValueError):
        gt.score_alignment()
    with pytest.raises(ValueError):
        gt.score_alignment(todo_id=1, ledger_id=2)


def test_score_alignment_against_ledger_row(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    gt.add_goal(tier="quarterly", title="Ledger goal", keywords=["ledger", "phase"])
    gt.add_goal(tier="weekly", title="Unrelated goal", keywords=["widgets"])

    conn = connect(db_path)
    try:
        result = append_ledger(
            conn, project="sb", summary="Shipped the ledger phase work", action_verb="Shipped"
        )
    finally:
        conn.close()

    scores = gt.score_alignment(ledger_id=result["id"])
    assert scores[0]["score"] > scores[1]["score"]
    assert scores[0]["score"] == 1.0


def test_score_alignment_zero_when_no_keyword_overlap(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    gt.add_goal(tier="weekly", title="Goal", keywords=["nonmatching"])

    conn = connect(db_path)
    try:
        result = append_ledger(conn, project="sb", summary="totally unrelated text", action_verb="Note")
    finally:
        conn.close()

    scores = gt.score_alignment(ledger_id=result["id"])
    assert scores[0]["score"] == 0.0


def test_heatmap_last_week_counts_matching_ledger_entries(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)

    goal = gt.add_goal(tier="quarterly", title="Ledger goal", keywords=["ledger"])

    conn = connect(db_path)
    try:
        append_ledger(
            conn,
            project="sb",
            summary="Shipped the ledger backend",
            action_verb="Shipped",
            refs=[{"kind": "pr", "value": "45"}],
        )
        append_ledger(conn, project="sb", summary="Unrelated widget work", action_verb="Note")
    finally:
        conn.close()

    heatmap = gt.heatmap_last_week()
    entry = next(h for h in heatmap if h["goal_id"] == goal["id"])
    assert entry["ledger_count"] == 1
    assert entry["top_refs"] == ["45"]


def test_heatmap_last_week_returns_empty_list_with_no_active_goals(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    assert gt.heatmap_last_week() == []
