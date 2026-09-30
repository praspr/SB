"""Round-trip dual-write tests for ledger_sync: SQLite <-> CHANGELOG.md."""

from __future__ import annotations

from pathlib import Path

from sb_core.ledger_sync import append_to_changelog, format_bullet, sync_from_files
from sb_core.store.db import connect
from sb_core.store.ledger import append_ledger, register_project, search_ledger


def test_format_bullet_with_scope_and_link_ref() -> None:
    row = {
        "ts": "2026-09-30T14:32:07Z",
        "action_verb": "Debugged",
        "summary": "APISIX 401 by adding token to Helm values",
        "refs": [{"kind": "pr", "value": "45", "label": "PR #45", "url": "https://example.com/pr/45"}],
        "scope": "cxp-priority-bugs-ai",
    }
    bullet = format_bullet(row)
    assert bullet == (
        "- **14:32:07 UTC** · **Debugged** APISIX 401 by adding token to Helm values "
        "[PR #45](https://example.com/pr/45) — *`cxp-priority-bugs-ai`*"
    )


def test_format_bullet_without_scope_or_refs() -> None:
    row = {
        "ts": "2026-09-30T09:00:00Z",
        "action_verb": "Shipped",
        "summary": "the ledger foundation",
        "refs": [],
        "scope": None,
    }
    bullet = format_bullet(row)
    assert bullet == "- **09:00:00 UTC** · **Shipped** the ledger foundation"


def test_append_to_changelog_creates_file_with_dated_heading(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    row = {
        "ts": "2026-09-30T14:32:07Z",
        "action_verb": "Debugged",
        "summary": "first entry",
        "refs": [],
        "scope": "sb",
    }
    append_to_changelog(changelog, row)
    text = changelog.read_text(encoding="utf-8")
    assert "# Changelog" in text
    assert "## [2026-09-30]" in text
    assert "- **14:32:07 UTC** · **Debugged** first entry — *`sb`*" in text


def test_append_to_changelog_inserts_new_bullet_as_first_under_heading(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [2026-09-30]\n- older bullet\n\n## [2026-09-29]\n- even older\n",
        encoding="utf-8",
    )
    row = {
        "ts": "2026-09-30T18:00:00Z",
        "action_verb": "Shipped",
        "summary": "newest entry",
        "refs": [],
        "scope": None,
    }
    append_to_changelog(changelog, row)
    text = changelog.read_text(encoding="utf-8")
    lines = text.splitlines()
    heading_idx = lines.index("## [2026-09-30]")
    assert lines[heading_idx + 1] == "- **18:00:00 UTC** · **Shipped** newest entry"
    assert lines[heading_idx + 2] == "- older bullet"
    # untouched older section
    assert "## [2026-09-29]" in text
    assert "- even older" in text


def test_append_to_changelog_respects_unreleased_convention(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    original = (
        "# Changelog\n\n"
        "## Unreleased\n\n"
        "### Added\n\n"
        "- some feature\n"
    )
    changelog.write_text(original, encoding="utf-8")
    row = {
        "ts": "2026-09-30T08:00:00Z",
        "action_verb": "Note",
        "summary": "first ledger promotion",
        "refs": [],
        "scope": None,
    }
    append_to_changelog(changelog, row)
    text = changelog.read_text(encoding="utf-8")
    assert "## Unreleased" in text
    assert "### Added" in text
    assert "- some feature" in text
    assert "## [2026-09-30]" in text
    # Dated section must come after Unreleased content, not disturb it.
    unreleased_pos = text.index("## Unreleased")
    dated_pos = text.index("## [2026-09-30]")
    added_pos = text.index("- some feature")
    assert unreleased_pos < added_pos < dated_pos


def test_append_to_changelog_preserves_existing_content_byte_for_byte_outside_touched_region(
    tmp_path: Path,
) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    original = "# Changelog\n\n## [2026-09-28]\n- **Debugged** something weird\n"
    changelog.write_text(original, encoding="utf-8")
    row = {
        "ts": "2026-09-30T08:00:00Z",
        "action_verb": "Note",
        "summary": "unrelated new entry",
        "refs": [],
        "scope": None,
    }
    append_to_changelog(changelog, row)
    text = changelog.read_text(encoding="utf-8")
    assert "- **Debugged** something weird" in text  # untouched legacy bullet


# NOTE: the end-to-end "ledger_log tool -> SQLite row + file bullet" round
# trip test lives in test_ledger_dualwrite_tools.py (added alongside
# ledger_tools.py), since it needs the MCP tool layer that module provides.


def test_sync_from_files_hydrates_hand_added_bullet(tmp_path: Path) -> None:
    db_path = tmp_path / "core.db"
    changelog_path = tmp_path / "proj" / "CHANGELOG.md"
    changelog_path.parent.mkdir(parents=True)
    changelog_path.write_text(
        "# Changelog\n\n## [2026-09-30]\n"
        "- **09:00:00 UTC** · **Debugged** hand added bullet — *`demo`*\n",
        encoding="utf-8",
    )

    conn = connect(db_path)
    try:
        register_project(
            conn,
            project="demo",
            root_path=str(tmp_path / "proj"),
            changelog_path=str(changelog_path),
            sync_mode="dual",
        )
        from sb_core.store.ledger import list_projects

        projects = list_projects(conn)
        result = sync_from_files(conn, projects)
        assert result["projects"]["demo"]["added"] == 1

        rows = search_ledger(conn, project="demo")
        assert len(rows) == 1
        assert rows[0]["summary"] == "hand added bullet"
        assert rows[0]["scope"] == "demo"

        # Running again is idempotent: no new rows, all skipped.
        result2 = sync_from_files(conn, projects)
        assert result2["projects"]["demo"]["added"] == 0
        assert result2["projects"]["demo"]["skipped"] == 1
    finally:
        conn.close()


def test_sync_from_files_never_writes_to_the_file(tmp_path: Path) -> None:
    db_path = tmp_path / "core.db"
    changelog_path = tmp_path / "proj" / "CHANGELOG.md"
    changelog_path.parent.mkdir(parents=True)
    original = "# Changelog\n\n## [2026-09-30]\n- **Legacy** bullet without timestamp\n"
    changelog_path.write_text(original, encoding="utf-8")

    conn = connect(db_path)
    try:
        register_project(
            conn,
            project="demo",
            root_path=str(tmp_path / "proj"),
            changelog_path=str(changelog_path),
        )
        from sb_core.store.ledger import list_projects

        sync_from_files(conn, list_projects(conn))
    finally:
        conn.close()

    assert changelog_path.read_text(encoding="utf-8") == original
