"""Tests for the goals YAML reader."""

from __future__ import annotations

from pathlib import Path

from sb_core.goals import load_goals

CATEGORIES = ("contractual", "quarterly", "weekly")


def test_missing_file_returns_empty_structure(tmp_path: Path) -> None:
    result = load_goals(tmp_path / "does-not-exist.yaml")
    assert set(result) == set(CATEGORIES)
    assert all(result[c] == [] for c in CATEGORIES)


def test_loads_all_categories(tmp_path: Path) -> None:
    p = tmp_path / "goals.yaml"
    p.write_text(
        """
contractual:
  - title: Ship SLA dashboard
    keywords: [sla, dashboard]
    active: true
quarterly:
  - title: Improve onboarding
    keywords: [onboarding]
weekly:
  - title: Clear review queue
    keywords: [review, pr]
""",
        encoding="utf-8",
    )
    result = load_goals(p)
    assert result["contractual"][0]["title"] == "Ship SLA dashboard"
    assert result["contractual"][0]["keywords"] == ["sla", "dashboard"]
    assert result["contractual"][0]["active"] is True
    assert result["quarterly"][0]["title"] == "Improve onboarding"
    assert result["weekly"][0]["keywords"] == ["review", "pr"]


def test_active_only_filters_inactive(tmp_path: Path) -> None:
    p = tmp_path / "goals.yaml"
    p.write_text(
        """
quarterly:
  - title: Active goal
    active: true
  - title: Retired goal
    active: false
""",
        encoding="utf-8",
    )
    active = load_goals(p, active_only=True)
    assert [g["title"] for g in active["quarterly"]] == ["Active goal"]

    everything = load_goals(p, active_only=False)
    assert {g["title"] for g in everything["quarterly"]} == {
        "Active goal",
        "Retired goal",
    }


def test_missing_active_defaults_to_active(tmp_path: Path) -> None:
    p = tmp_path / "goals.yaml"
    p.write_text(
        "weekly:\n  - title: No active flag\n    keywords: [x]\n",
        encoding="utf-8",
    )
    result = load_goals(p, active_only=True)
    assert result["weekly"][0]["title"] == "No active flag"


def test_malformed_yaml_returns_empty_structure(tmp_path: Path) -> None:
    p = tmp_path / "goals.yaml"
    p.write_text("this: is: not: valid: yaml: [", encoding="utf-8")
    result = load_goals(p)
    assert set(result) == set(CATEGORIES)
    assert all(result[c] == [] for c in CATEGORIES)


def test_non_mapping_yaml_returns_empty_structure(tmp_path: Path) -> None:
    p = tmp_path / "goals.yaml"
    p.write_text("- just\n- a\n- list\n", encoding="utf-8")
    result = load_goals(p)
    assert all(result[c] == [] for c in CATEGORIES)
