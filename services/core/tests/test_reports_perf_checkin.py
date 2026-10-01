"""Tests for sb_core.reports.perf_checkin: week slicing, evidence parsing,
LLM narration with deterministic fallback."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from sb_core.reports import perf_checkin as pc


# ---------------------------------------------------------------------------
# _previous_week
# ---------------------------------------------------------------------------


def test_previous_week_from_monday() -> None:
    # 2026-09-28 is a Monday.
    today = date(2026, 9, 28)
    assert today.weekday() == 0
    start, end = pc._previous_week(today)
    assert start == date(2026, 9, 21)
    assert end == date(2026, 9, 27)


def test_previous_week_from_sunday() -> None:
    # 2026-10-04 is a Sunday, in the same calendar week as the Monday above.
    today = date(2026, 10, 4)
    assert today.weekday() == 6
    start, end = pc._previous_week(today)
    assert start == date(2026, 9, 21)
    assert end == date(2026, 9, 27)


@pytest.mark.parametrize(
    "offset,expected_weekday",
    [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)],
)
def test_previous_week_from_tuesday_through_saturday(offset: int, expected_weekday: int) -> None:
    # 2026-09-28 (Mon) + offset gives Tue..Sat in the same week.
    today = date(2026, 9, 28) + timedelta(days=offset)
    assert today.weekday() == expected_weekday
    start, end = pc._previous_week(today)
    assert start == date(2026, 9, 21)
    assert end == date(2026, 9, 27)


def test_previous_week_is_always_seven_days() -> None:
    for day_offset in range(7):
        today = date(2026, 9, 28) + timedelta(days=day_offset)
        start, end = pc._previous_week(today)
        assert (end - start).days == 6


# ---------------------------------------------------------------------------
# _slice_evidence
# ---------------------------------------------------------------------------


_TWO_WEEK_CHANGELOG = """# Changelog

## [2026-09-30]
- **Debugged** something in the newer week — *`ciq`*

## [2026-09-28]
- **Shipped** the Monday item for the newer week — *`ciq`*

## [2026-09-25]
- **Reviewed** an older-week item — *`ciq`*

## [2026-09-21]
- **Drafted** the oldest-week Monday item — *`ciq`*
"""


def test_slice_evidence_returns_only_requested_week(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(_TWO_WEEK_CHANGELOG, encoding="utf-8")

    result = pc._slice_evidence(changelog, date(2026, 9, 21), date(2026, 9, 27))
    days = [day for day, _ in result]
    assert days == [date(2026, 9, 21), date(2026, 9, 25)]
    assert any("oldest-week Monday item" in b for _, bullets in result for b in bullets)
    assert not any("newer week" in b for _, bullets in result for b in bullets)


def test_slice_evidence_missing_file_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.md"
    assert pc._slice_evidence(missing, date(2026, 9, 21), date(2026, 9, 27)) == []


def test_slice_evidence_ignores_non_bullet_lines(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [2026-09-21]\nSome prose, not a bullet.\n- **Shipped** a real bullet\n",
        encoding="utf-8",
    )
    result = pc._slice_evidence(changelog, date(2026, 9, 21), date(2026, 9, 27))
    assert result == [(date(2026, 9, 21), ["- **Shipped** a real bullet"])]


# ---------------------------------------------------------------------------
# perf_checkin (integration, via env var path overrides)
# ---------------------------------------------------------------------------


@pytest.fixture
def ciq_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    changelog = tmp_path / "ciq-CHANGELOG.md"
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill\nFull vs one-improvement rules.", encoding="utf-8")
    (skill_dir / "examples.md").write_text("# Examples\nSome examples.", encoding="utf-8")
    (skill_dir / "guiding-principles.md").write_text("# Guiding Principles\nBe clear.", encoding="utf-8")
    monkeypatch.setenv("SB_PERF_CHECKIN_CHANGELOG_PATH", str(changelog))
    monkeypatch.setenv("SB_PERF_CHECKIN_SKILL_DIR", str(skill_dir))
    return changelog


def test_perf_checkin_returns_expected_shape(ciq_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ciq_env.write_text("# Changelog\n\n## [2026-09-21]\n- **Shipped** the thing — *`ciq`*\n", encoding="utf-8")

    from sb_core import llm as llm_mod

    monkeypatch.setattr(llm_mod, "complete", lambda prompt, model=None: "Narrated weekly check-in.")

    result = pc.perf_checkin(today=date(2026, 9, 28), shape="full", voice="first-person")
    assert set(result.keys()) == {"markdown", "citations", "range", "shape", "voice"}
    assert result["shape"] == "full"
    assert result["voice"] == "first-person"
    assert result["range"] == {"from": "2026-09-21", "to": "2026-09-27"}
    assert result["markdown"] == "Narrated weekly check-in."
    assert result["citations"]


def test_perf_checkin_falls_back_when_llm_raises(ciq_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ciq_env.write_text("# Changelog\n\n## [2026-09-21]\n- **Shipped** the thing — *`ciq`*\n", encoding="utf-8")

    from sb_core import llm as llm_mod

    def _raise(prompt, model=None):
        raise llm_mod.LLMUnavailable("down")

    monkeypatch.setattr(llm_mod, "complete", _raise)

    result = pc.perf_checkin(today=date(2026, 9, 28))
    assert "LLM narration unavailable" in result["markdown"]
    assert "Shipped" in result["markdown"]


def test_perf_checkin_falls_back_on_empty_week(ciq_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ciq_env.write_text("# Changelog\n\n## [2026-01-01]\n- **Shipped** unrelated — *`ciq`*\n", encoding="utf-8")

    from sb_core import llm as llm_mod

    def _should_not_be_called(prompt, model=None):
        raise AssertionError("LLM must not be called when there is no evidence")

    monkeypatch.setattr(llm_mod, "complete", _should_not_be_called)

    result = pc.perf_checkin(today=date(2026, 9, 28))
    assert "No ciq CHANGELOG entries found for this week." in result["markdown"]
    assert result["citations"] == []


def test_perf_checkin_falls_back_on_empty_llm_response(ciq_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ciq_env.write_text("# Changelog\n\n## [2026-09-21]\n- **Shipped** the thing — *`ciq`*\n", encoding="utf-8")

    from sb_core import llm as llm_mod

    monkeypatch.setattr(llm_mod, "complete", lambda prompt, model=None: "   ")

    result = pc.perf_checkin(today=date(2026, 9, 28))
    assert "LLM narration unavailable" in result["markdown"]


def test_perf_checkin_one_improvement_shape_builds_under_500_constraint(
    ciq_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ciq_env.write_text("# Changelog\n\n## [2026-09-21]\n- **Shipped** the thing — *`ciq`*\n", encoding="utf-8")

    from sb_core import llm as llm_mod

    captured_prompt = {}

    def _capture(prompt, model=None):
        captured_prompt["value"] = prompt
        return "One improvement answer."

    monkeypatch.setattr(llm_mod, "complete", _capture)

    result = pc.perf_checkin(today=date(2026, 9, 28), shape="one-improvement", voice="third-person")
    assert result["shape"] == "one-improvement"
    assert result["voice"] == "third-person"
    assert "under 500" in captured_prompt["value"]
    assert "Voice: third-person." in captured_prompt["value"]


def test_default_paths_point_at_ciq() -> None:
    assert str(pc._DEFAULT_CHANGELOG).endswith("code_home/ciq/CHANGELOG.md")
    assert str(pc._DEFAULT_SKILL_DIR).endswith(
        "code_home/ciq/.cursor/skills/cisco-iq-performance-checkin"
    )
