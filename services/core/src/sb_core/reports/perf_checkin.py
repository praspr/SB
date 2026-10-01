"""Cisco weekly check-in template.

Reads ciq CHANGELOG.md for the previous ISO calendar week (Mon-Sun), loads
the cisco-iq-performance-checkin skill files as system context, calls the
LLM with the user's chosen shape + voice, and returns markdown.

Evidence scope is deliberately narrow: ONLY
``~/Documents/code_home/ciq/CHANGELOG.md`` (override via
``SB_PERF_CHECKIN_CHANGELOG_PATH``) -- never sb's own ledger or
CHANGELOG.md, never any other repo.

Deterministic fallback: evidence lines verbatim with a 'no LLM' header.
Never raises for an LLM-unavailable or empty-evidence reason.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CHANGELOG = Path("~/Documents/code_home/ciq/CHANGELOG.md").expanduser()
_DEFAULT_SKILL_DIR = Path(
    "~/Documents/code_home/ciq/.cursor/skills/cisco-iq-performance-checkin"
).expanduser()
_HEADING_RE = re.compile(r"^##\s+\[(\d{4}-\d{2}-\d{2})\]")

_VALID_SHAPES = ("full", "one-improvement")
_VALID_VOICES = ("first-person", "third-person")


def _resolve_paths() -> tuple[Path, Path]:
    changelog = Path(
        os.environ.get("SB_PERF_CHECKIN_CHANGELOG_PATH", str(_DEFAULT_CHANGELOG))
    ).expanduser()
    skill = Path(
        os.environ.get("SB_PERF_CHECKIN_SKILL_DIR", str(_DEFAULT_SKILL_DIR))
    ).expanduser()
    return changelog, skill


def _previous_week(today: date) -> tuple[date, date]:
    """Return (monday, sunday) of the previous ISO calendar week.

    If *today* is itself a Monday, "this week" has not started per the
    skill's evidence-first rule, so the previous week is simply the most
    recently completed Mon-Sun -- the same math applies uniformly regardless
    of which weekday *today* is.
    """
    weekday = today.weekday()  # Mon=0 .. Sun=6
    this_monday = today - timedelta(days=weekday)
    prev_monday = this_monday - timedelta(days=7)
    prev_sunday = this_monday - timedelta(days=1)
    return prev_monday, prev_sunday


def _slice_evidence(
    path: Path, week_start: date, week_end: date
) -> list[tuple[date, list[str]]]:
    """Return [(date, [bullets])] for days in [week_start, week_end]."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[date, list[str]] = {}
    current: date | None = None
    for raw_line in text.splitlines():
        m = _HEADING_RE.match(raw_line.strip())
        if m:
            try:
                current = date.fromisoformat(m.group(1))
            except ValueError:
                current = None
            continue
        line = raw_line.rstrip()
        if current and week_start <= current <= week_end and line.startswith("- "):
            out.setdefault(current, []).append(line)
    return sorted(out.items())


def _load_skill_context(skill_dir: Path) -> dict[str, str]:
    """Load SKILL.md + examples.md + guiding-principles.md as a dict.

    Missing files are silently skipped (best-effort context; never raises).
    """
    out: dict[str, str] = {}
    for name in ("SKILL.md", "examples.md", "guiding-principles.md"):
        p = skill_dir / name
        if p.exists():
            out[name] = p.read_text(encoding="utf-8", errors="replace")
    return out


def _deterministic_fallback(
    evidence: list[tuple[date, list[str]]],
    week_start: date,
    week_end: date,
    shape: str,
    voice: str,
) -> str:
    header = (
        "# Weekly check-in evidence (LLM narration unavailable)\n\n"
        f"**Week**: {week_start.isoformat()} to {week_end.isoformat()} · "
        f"**Shape**: {shape} · **Voice**: {voice}\n\n"
    )
    if not evidence:
        return header + "No ciq CHANGELOG entries found for this week.\n"
    lines = [header]
    for day, bullets in evidence:
        lines.append(f"## {day.isoformat()}\n")
        lines.extend(bullets)
        lines.append("")
    return "\n".join(lines)


def _build_system_prompt(skill: dict[str, str], shape: str, voice: str) -> str:
    skill_blob = "\n\n---\n\n".join(
        f"# {name}\n\n{text}" for name, text in skill.items()
    )
    constraints = []
    if shape == "one-improvement":
        constraints.append(
            "Produce a single-question 'one improvement' response, under 500 "
            "characters, outcome language only."
        )
    else:
        constraints.append(
            "Produce a full weekly check-in covering current priorities and "
            "progress, completed work, evolving work, and areas of need, plus "
            "a Guiding Principles line."
        )
    constraints.append(f"Voice: {voice}.")
    return (
        "You are drafting a Cisco weekly check-in for Prasad. Apply the rules "
        "in the following skill content exactly.\n\n"
        + skill_blob
        + "\n\n## This response\n"
        + "\n".join(f"- {c}" for c in constraints)
    )


def _build_user_prompt(
    evidence: list[tuple[date, list[str]]],
    week_start: date,
    week_end: date,
    shape: str,
    voice: str,
) -> str:
    lines = [
        f"Week: {week_start.isoformat()} (Mon) to {week_end.isoformat()} (Sun).",
        f"Shape: {shape}. Voice: {voice}.",
        "",
        "## Evidence from ciq/CHANGELOG.md",
    ]
    for day, bullets in evidence:
        lines.append(f"\n### {day.isoformat()}")
        lines.extend(bullets)
    return "\n".join(lines)


def perf_checkin(
    *,
    today: date | None = None,
    shape: str = "full",
    voice: str = "first-person",
) -> dict[str, Any]:
    """Draft a Cisco weekly check-in from ciq CHANGELOG evidence.

    shape: 'full' (4-purpose weekly + Guiding Principles) or
        'one-improvement' (under 500 chars).
    voice: 'first-person' or 'third-person'.

    Returns ``{"markdown", "citations", "range", "shape", "voice"}``. Never
    raises: an unavailable LLM backend or empty evidence both fall back to a
    deterministic markdown dump.
    """
    today = today or date.today()
    week_start, week_end = _previous_week(today)
    changelog, skill_dir = _resolve_paths()
    evidence = _slice_evidence(changelog, week_start, week_end)
    skill = _load_skill_context(skill_dir)

    citations: list[str] = []
    for day, bullets in evidence:
        for bullet in bullets:
            citations.append(f"{day.isoformat()}: {bullet[:120]}")

    range_meta = {"from": week_start.isoformat(), "to": week_end.isoformat()}

    try:
        from .. import llm as llm_mod
        from ..config import settings

        if not evidence:
            raise llm_mod.LLMUnavailable("no evidence for the previous week")

        system_prompt = _build_system_prompt(skill, shape, voice)
        user_prompt = _build_user_prompt(evidence, week_start, week_end, shape, voice)
        # sb_core.llm.complete() takes a single prompt string (no separate
        # system/user split) -- fold the system context in first, matching
        # every other LLM call in this codebase (ritual_tools, chat_tools,
        # triage_tools all do the same single-prompt pattern).
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        narration = llm_mod.complete(combined_prompt, model=settings.llm_model)
        if not narration or not narration.strip():
            raise llm_mod.LLMUnavailable("empty LLM response")
        return {
            "markdown": narration,
            "citations": citations,
            "range": range_meta,
            "shape": shape,
            "voice": voice,
        }
    except Exception as exc:  # noqa: BLE001 -- any LLM/transport failure falls back
        logger.warning("perf_checkin LLM narration failed: %s", exc)
        markdown = _deterministic_fallback(evidence, week_start, week_end, shape, voice)
        return {
            "markdown": markdown,
            "citations": citations,
            "range": range_meta,
            "shape": shape,
            "voice": voice,
        }
