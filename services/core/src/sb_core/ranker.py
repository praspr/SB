"""Pure, deterministic ranker over open todos.

No LLM, no I/O.  Priority and overdue due dates dominate; goal keyword
alignment adds a boost; domain contributes a small weight.  Each ranked item
carries a numeric ``score`` and a human-readable ``rationale``.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

# Priority weight: lower priority number (P1) is more important.
_PRIORITY_WEIGHT = {1: 40, 2: 30, 3: 20, 4: 10}
_DEFAULT_PRIORITY_WEIGHT = 10

_OVERDUE_BOOST = 50
_DUE_TODAY_BOOST = 25
_GOAL_MATCH_BOOST = 15  # per aligned goal (not per keyword)
_DOMAIN_WEIGHT = {"work": 3}
_DEFAULT_DOMAIN_WEIGHT = 1


def _iter_goals(goals: Optional[dict]) -> list[dict]:
    if not goals:
        return []
    result: list[dict] = []
    for category in ("contractual", "quarterly", "weekly"):
        for goal in goals.get(category, []) or []:
            if goal.get("active", True):
                result.append(goal)
    return result


def _priority_of(todo: dict) -> int:
    try:
        return int(todo.get("priority", 4))
    except (TypeError, ValueError):
        return 4


def rank_todos(
    todos: list[dict],
    goals: Optional[dict] = None,
    *,
    today: Optional[str] = None,
) -> list[dict]:
    """Rank *todos* deterministically, returning a new list (highest first).

    Each returned dict is a shallow copy of the input todo plus ``score``
    (int) and ``rationale`` (str).  Ordering is stable: ties break by priority,
    then earliest due date, then id.
    """
    today_str = today or date.today().isoformat()
    active_goals = _iter_goals(goals)

    ranked: list[dict] = []
    for index, todo in enumerate(todos):
        priority = _priority_of(todo)
        score = _PRIORITY_WEIGHT.get(priority, _DEFAULT_PRIORITY_WEIGHT)
        reasons = [f"priority P{priority}"]

        due = (todo.get("due_date") or "").strip()
        if due:
            if due < today_str:
                score += _OVERDUE_BOOST
                reasons.append(f"overdue (due {due})")
            elif due == today_str:
                score += _DUE_TODAY_BOOST
                reasons.append("due today")

        text = f"{todo.get('title', '')} {todo.get('description', '')}".lower()
        matched_keywords: list[str] = []
        for goal in active_goals:
            hit = next(
                (kw for kw in goal.get("keywords", []) if kw and kw.lower() in text),
                None,
            )
            if hit:
                score += _GOAL_MATCH_BOOST
                matched_keywords.append(hit.lower())
        if matched_keywords:
            reasons.append(
                "aligns with goals via: " + ", ".join(sorted(set(matched_keywords)))
            )

        domain = todo.get("domain") or "work"
        score += _DOMAIN_WEIGHT.get(domain, _DEFAULT_DOMAIN_WEIGHT)

        item = dict(todo)
        item["score"] = score
        item["rationale"] = "; ".join(reasons)
        ranked.append(
            (index, priority, due or "9999-99-99", todo.get("id", index), item)
        )

    ranked.sort(key=lambda t: (-t[4]["score"], t[1], t[2], t[3]))
    return [t[4] for t in ranked]
