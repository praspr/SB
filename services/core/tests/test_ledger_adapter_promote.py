"""synthetic CHANGELOG.md through the changelog adapter -> signal + promoted ledger row."""

from __future__ import annotations

from pathlib import Path

from sb_core.adapters.changelog import run as run_changelog_adapter
from sb_core.store.db import connect
from sb_core.store.ledger import register_project, search_ledger


def _write_changelog(root: Path, text: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "CHANGELOG.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_changelog_adapter_still_produces_version_signal(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    _write_changelog(
        root,
        "# Changelog\n\n## [1.2.0] - 2026-09-01\n- Some release note\n",
    )
    conn = connect(tmp_path / "core.db")
    try:
        count = run_changelog_adapter(conn, roots=[root])
        assert count == 1
        row = conn.execute("SELECT * FROM sb_signals WHERE source = 'changelog'").fetchone()
        assert row is not None
        assert "1.2.0" in row["title"]
    finally:
        conn.close()


def test_changelog_adapter_promotes_bullets_for_registered_project(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    _write_changelog(
        root,
        (
            "# Changelog\n\n"
            "## [2026-09-30]\n"
            "- **09:15:00 UTC** · **Debugged** APISIX 401 by adding token to Helm values "
            "[PR #45](https://example.com/pr/45) — *`demo-scope`*\n"
        ),
    )
    conn = connect(tmp_path / "core.db")
    try:
        register_project(conn, project="demo", root_path=str(root))
        promoted_count = run_changelog_adapter(conn, roots=[root])
        # Version-heading signal count is unaffected (0, since there is no
        # version heading in this file) -- the return contract stays an int.
        assert promoted_count == 0

        ledger_rows = search_ledger(conn, project="demo")
        assert len(ledger_rows) == 1
        row = ledger_rows[0]
        assert row["action_verb"] == "Debugged"
        assert "APISIX 401" in row["summary"]
        assert row["scope"] == "demo-scope"
        assert row["source_harness"] == "changelog-adapter"
        assert row["origin"] == "adapter-promote"
    finally:
        conn.close()


def test_changelog_adapter_does_not_promote_unregistered_project(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    _write_changelog(
        root,
        "# Changelog\n\n## [2026-09-30]\n- **09:15:00 UTC** · **Debugged** unregistered project bullet\n",
    )
    conn = connect(tmp_path / "core.db")
    try:
        run_changelog_adapter(conn, roots=[root])
        ledger_rows = search_ledger(conn, project="unregistered")
        assert ledger_rows == []
        all_rows = conn.execute("SELECT COUNT(*) AS n FROM sb_ledger").fetchone()
        assert all_rows["n"] == 0
    finally:
        conn.close()


def test_changelog_adapter_promotion_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    _write_changelog(
        root,
        "# Changelog\n\n## [2026-09-30]\n- **09:15:00 UTC** · **Shipped** idempotent bullet\n",
    )
    conn = connect(tmp_path / "core.db")
    try:
        register_project(conn, project="demo", root_path=str(root))
        run_changelog_adapter(conn, roots=[root])
        run_changelog_adapter(conn, roots=[root])
        rows = search_ledger(conn, project="demo")
        assert len(rows) == 1
    finally:
        conn.close()
