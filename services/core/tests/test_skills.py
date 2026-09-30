"""Allow-listed skill discovery, hashing, and MCP prompt registration."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from sb_core.mcp_app import mcp
from sb_core.skills import MAX_SKILL_BYTES, get_skill, list_skills, sync_skills
from sb_core.store.db import connect

_BODY = """---
name: {name}
description: {description}
---
# {name}

## Allowed tools
- `example_tool`

## Procedure
Use the tool for {description}.
"""


def _write(
    root: Path, skill_id: str, description: str, name: str | None = None
) -> Path:
    directory = root / skill_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "SKILL.md"
    path.write_text(
        _BODY.format(name=name or skill_id, description=description),
        encoding="utf-8",
    )
    return path


def _sync(db: Path, roots: list[tuple[str, Path]]) -> dict[str, int]:
    conn = connect(db)
    try:
        return sync_skills(conn, roots)
    finally:
        conn.close()


def test_discovery_covers_sources_duplicates_and_rejects(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    cursor = tmp_path / "cursor"
    claude = tmp_path / "claude"
    configured = tmp_path / "configured"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text(
        _BODY.format(name="secret", description="outside the root"),
        encoding="utf-8",
    )

    _write(project, "alpha", "from project")
    _write(cursor, "alpha", "from cursor")
    _write(claude, "bravo", "from claude")
    _write(configured, "charlie", "from configured")
    _write(project, "broken", "will be overwritten")
    (project / "broken" / "SKILL.md").write_text("not frontmatter\n", encoding="utf-8")
    huge = project / "huge"
    huge.mkdir()
    (huge / "SKILL.md").write_bytes(b"x" * (MAX_SKILL_BYTES + 1))
    escaped = project / "escaped"
    escaped.symlink_to(outside, target_is_directory=True)

    db = tmp_path / "core.db"
    roots = [
        ("project", project),
        ("cursor", cursor),
        ("claude", claude),
        ("configured", configured),
    ]
    first = _sync(db, roots)
    assert first["duplicates"] == 1
    assert first["added"] == 5  # alpha, bravo, charlie, broken, huge

    conn = connect(db)
    try:
        by_id = {row["id"]: row for row in list_skills(conn)}
        assert by_id["alpha"]["description"] == "from project"
        assert by_id["alpha"]["source"] == "project"
        assert by_id["bravo"]["source"] == "claude"
        assert by_id["charlie"]["source"] == "configured"
        assert by_id["broken"]["available"] is False
        assert by_id["huge"]["available"] is False
        assert "escaped" not in by_id
        assert "secret" not in by_id
        alpha = get_skill(conn, "alpha")
        assert alpha is not None
        assert alpha["path"] == "SKILL.md"
        assert "example_tool" in alpha["allowed_tools"]
        assert alpha["content_sha256"]
        assert len(alpha["content_sha256"]) == 64
    finally:
        conn.close()

    second = _sync(db, roots)
    assert second["added"] == 0
    assert second["updated"] == 0

    _write(project, "alpha", "from project revised")
    third = _sync(db, roots)
    assert third["updated"] == 1
    conn = connect(db)
    try:
        assert get_skill(conn, "alpha")["description"] == "from project revised"
    finally:
        conn.close()

    (project / "bravo").mkdir(exist_ok=True)
    # bravo lives under claude; removing that file marks it unavailable
    (claude / "bravo" / "SKILL.md").unlink()
    fourth = _sync(db, roots)
    assert fourth["unavailable"] == 1
    conn = connect(db)
    try:
        missing = get_skill(conn, "bravo")
        assert missing is not None
        assert missing["available"] is False
    finally:
        conn.close()


def test_prompt_and_resource_match_enabled_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    _write(project, "alpha", "visible skill")
    _write(project, "broken", "nope")
    (project / "broken" / "SKILL.md").write_text("nope\n", encoding="utf-8")

    from sb_core import skills as skills_module
    from sb_core.config import settings

    db = tmp_path / "skills.db"
    monkeypatch.setattr(settings, "db_path", db)
    monkeypatch.setattr(skills_module, "default_roots", lambda: [("project", project)])

    async def scenario() -> tuple[set[str], set[str]]:
        result = await mcp.call_tool("sync_skills", {})
        prompts = {prompt.name for prompt in await mcp.list_prompts()}
        resources = {str(resource.uri) for resource in await mcp.list_resources()}
        assert getattr(result, "structured_content", result)
        return prompts, resources

    prompts, resources = asyncio.run(scenario())
    assert "skill_alpha" in prompts
    assert "skill://alpha" in resources
    assert "skill_broken" not in prompts


def test_list_skills_filters(tmp_path: Path) -> None:
    project = tmp_path / "project"
    cursor = tmp_path / "cursor"
    _write(project, "alpha", "plan the day")
    _write(cursor, "signals", "search evidence")
    db = tmp_path / "core.db"
    _sync(db, [("project", project), ("cursor", cursor)])
    conn = connect(db)
    try:
        found = list_skills(conn, source="cursor", query="evidence")
        assert [item["id"] for item in found] == ["signals"]
    finally:
        conn.close()
