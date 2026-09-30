"""Tests for the deterministic todo ranker (no LLM)."""

from __future__ import annotations

from sb_core.ranker import rank_todos

TODAY = "2026-09-30"


def _todo(**kw) -> dict:
    base = {
        "id": kw.get("id", 1),
        "title": "Task",
        "description": "",
        "priority": 3,
        "due_date": None,
        "domain": "work",
    }
    base.update(kw)
    return base


def test_returns_score_and_rationale_for_each_todo() -> None:
    ranked = rank_todos([_todo(id=1)], goals=None, today=TODAY)
    assert len(ranked) == 1
    assert isinstance(ranked[0]["score"], (int, float))
    assert isinstance(ranked[0]["rationale"], str)
    assert ranked[0]["rationale"]
    assert ranked[0]["id"] == 1


def test_higher_priority_outranks_lower_priority() -> None:
    todos = [_todo(id=1, priority=4), _todo(id=2, priority=1)]
    ranked = rank_todos(todos, goals=None, today=TODAY)
    assert ranked[0]["id"] == 2
    assert ranked[0]["score"] > ranked[1]["score"]


def test_overdue_outranks_not_due_at_same_priority() -> None:
    todos = [
        _todo(id=1, priority=2, due_date=None),
        _todo(id=2, priority=2, due_date="2026-01-01"),  # overdue
    ]
    ranked = rank_todos(todos, goals=None, today=TODAY)
    assert ranked[0]["id"] == 2


def test_goal_keyword_alignment_boosts_and_shows_in_rationale() -> None:
    goals = {
        "quarterly": [
            {"title": "Dashboards", "keywords": ["dashboard"], "active": True}
        ],
        "contractual": [],
        "weekly": [],
    }
    todos = [
        _todo(id=1, priority=3, title="Write report"),
        _todo(id=2, priority=3, title="Build dashboard widget"),
    ]
    ranked = rank_todos(todos, goals=goals, today=TODAY)
    aligned = next(r for r in ranked if r["id"] == 2)
    other = next(r for r in ranked if r["id"] == 1)
    assert aligned["score"] > other["score"]
    assert "dashboard" in aligned["rationale"].lower()


def test_ranking_is_deterministic() -> None:
    goals = {
        "quarterly": [{"title": "X", "keywords": ["deploy"], "active": True}],
        "contractual": [],
        "weekly": [],
    }
    todos = [
        _todo(id=1, priority=2, title="deploy service", due_date="2026-01-01"),
        _todo(id=2, priority=1, title="review pr"),
        _todo(id=3, priority=4, title="tidy notes"),
    ]
    first = rank_todos(todos, goals=goals, today=TODAY)
    second = rank_todos(list(reversed(todos)), goals=goals, today=TODAY)
    assert [r["id"] for r in first] == [r["id"] for r in second]
    assert [r["score"] for r in first] == [r["score"] for r in second]


def test_empty_input_returns_empty_list() -> None:
    assert rank_todos([], goals=None, today=TODAY) == []
