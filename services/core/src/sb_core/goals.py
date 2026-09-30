"""Safe reader for the goals YAML file.

Goals schema (all sections optional)::

    contractual:            # long-lived commitments
      - title: str          # required, human-readable
        keywords: [str]     # optional, used by the ranker for alignment
        active: bool        # optional, defaults to true
    quarterly:              # same item shape
      - ...
    weekly:                 # same item shape
      - ...

A missing or malformed file yields an empty structured result (never raises).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

CATEGORIES: tuple[str, ...] = ("contractual", "quarterly", "weekly")


def _empty() -> dict[str, list]:
    return {category: [] for category in CATEGORIES}


def _normalize_goal(item: dict) -> dict:
    active = item.get("active", True)
    keywords = item.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = []
    return {
        "title": str(item.get("title", "")),
        "keywords": [str(k) for k in keywords],
        "active": bool(active),
    }


def load_goals(
    path: Optional[Path | str] = None, *, active_only: bool = True
) -> dict[str, list]:
    """Read the goals YAML, returning a structured dict keyed by category.

    Missing files, malformed YAML, or non-mapping documents all return the
    empty structure rather than raising.
    """
    if path is None:
        from .config import settings

        path = settings.goals_path
    p = Path(path).expanduser()

    result = _empty()
    if not p.is_file():
        return result

    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return result
    if not isinstance(raw, dict):
        return result

    for category in CATEGORIES:
        items = raw.get(category)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            goal = _normalize_goal(item)
            if active_only and not goal["active"]:
                continue
            result[category].append(goal)
    return result


def active_keywords(goals: dict[str, list]) -> list[str]:
    """Flatten all keywords across active goals (deduped, order-preserving)."""
    seen: dict[str, None] = {}
    for category in CATEGORIES:
        for goal in goals.get(category, []):
            if not goal.get("active", True):
                continue
            for keyword in goal.get("keywords", []):
                seen.setdefault(keyword.lower(), None)
    return list(seen)
