"""Exercise each of the 9 ledger MCP tools via monkeypatched _get_conn."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import sb_core.ledger_tools as lt
from sb_core.store.db import connect
from sb_core.store.ledger import append_ledger, register_project


def _patch_conn(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    monkeypatch.setattr(lt, "_get_conn", lambda: connect(db_path))


def test_all_nine_tools_are_registered() -> None:
    tools = asyncio.run(lt.mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "ledger_log",
        "ledger_batch_log",
        "ledger_search",
        "ledger_context",
        "ledger_by_ref",
        "ledger_open_threads",
        "ledger_projects",
        "ledger_register_project",
        "sync_ledger_from_files",
    }
    assert expected <= names


def test_ledger_tools_are_mounted_on_parent_mcp() -> None:
    from sb_core.mcp_app import mcp as parent

    tools = asyncio.run(parent.list_tools())
    names = {t.name for t in tools}
    assert "ledger_log" in names
    assert "sync_ledger_from_files" in names


def test_ledger_log_inserts_row_and_returns_shape(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    result = lt.ledger_log(summary="First entry", project="sb", action_verb="Shipped")
    assert result["was_new"] is True
    assert result["persisted_to_file"] is False  # sb not registered in this fresh db
    assert result["session_id"]


def test_ledger_log_is_idempotent(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    first = lt.ledger_log(summary="Same content", project="sb")
    second = lt.ledger_log(summary="Same content", project="sb")
    assert first["id"] == second["id"]
    assert second["was_new"] is False


def test_ledger_log_writes_to_changelog_when_dual_mode(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    changelog = tmp_path / "proj" / "CHANGELOG.md"

    conn = connect(db_path)
    try:
        register_project(
            conn, project="demo", root_path=str(tmp_path / "proj"), changelog_path=str(changelog), sync_mode="dual"
        )
    finally:
        conn.close()

    result = lt.ledger_log(summary="Dual write entry", project="demo", action_verb="Shipped")
    assert result["persisted_to_file"] is True
    assert changelog.is_file()
    text = changelog.read_text(encoding="utf-8")
    assert "Dual write entry" in text


def test_ledger_batch_log_processes_all_entries(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    result = lt.ledger_batch_log(
        [
            {"summary": "entry one", "project": "sb"},
            {"summary": "entry two", "project": "sb"},
        ]
    )
    assert len(result["results"]) == 2
    assert all(r.get("was_new") for r in result["results"])


def test_ledger_search_filters_by_project(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    lt.ledger_log(summary="sb one", project="sb")
    lt.ledger_log(summary="ciq one", project="ciq")

    results = lt.ledger_search(project="sb")
    assert len(results) == 1
    assert results[0]["project"] == "sb"


def test_ledger_context_returns_expected_shape(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    lt.ledger_log(summary="context entry", project="sb")
    context = lt.ledger_context(project="sb")
    assert set(context.keys()) == {"entries", "open_threads", "tracked_refs"}


def test_ledger_by_ref_matches(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    lt.ledger_log(
        summary="linked pr",
        project="sb",
        refs=[{"kind": "pr", "value": "45"}],
    )
    matches = lt.ledger_by_ref(kind="pr", value="45")
    assert len(matches) == 1


def test_ledger_open_threads_returns_list(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    lt.ledger_log(summary="entry", project="sb")
    threads = lt.ledger_open_threads(project="sb")
    assert isinstance(threads, list)


def test_ledger_projects_lists_enrolled_projects(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    lt.ledger_register_project(project="demo", root_path=str(tmp_path / "demo"))
    projects = lt.ledger_projects()
    assert any(p["project"] == "demo" for p in projects)


def test_ledger_register_project_defaults_changelog_path(tmp_path, monkeypatch) -> None:
    _patch_conn(monkeypatch, tmp_path / "core.db")
    result = lt.ledger_register_project(project="demo", root_path=str(tmp_path / "demo"))
    assert result["changelog_path"] == str(tmp_path / "demo" / "CHANGELOG.md")
    assert result["sync_mode"] == "dual"


def test_sync_ledger_from_files_hydrates_registered_projects(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    changelog = tmp_path / "demo" / "CHANGELOG.md"
    changelog.parent.mkdir(parents=True)
    changelog.write_text(
        "# Changelog\n\n## [2026-09-30]\n- **09:00:00 UTC** · **Debugged** hydrated bullet\n",
        encoding="utf-8",
    )
    lt.ledger_register_project(project="demo", root_path=str(tmp_path / "demo"), changelog_path=str(changelog))

    result = lt.sync_ledger_from_files()
    assert result["projects"]["demo"]["added"] == 1

    rows = lt.ledger_search(project="demo")
    assert len(rows) == 1
    assert rows[0]["summary"] == "hydrated bullet"


# ---------------------------------------------------------------------------
# sync_ledger_from_files — lock + record_sync wiring (phase 2j)
# ---------------------------------------------------------------------------


def test_sync_ledger_from_files_records_sync_with_per_project_counts(
    tmp_path, monkeypatch
) -> None:
    db_path = tmp_path / "core.db"
    _patch_conn(monkeypatch, db_path)
    changelog = tmp_path / "demo" / "CHANGELOG.md"
    changelog.parent.mkdir(parents=True)
    changelog.write_text(
        "# Changelog\n\n## [2026-09-30]\n- **09:00:00 UTC** · **Debugged** hydrated bullet\n",
        encoding="utf-8",
    )
    lt.ledger_register_project(
        project="demo", root_path=str(tmp_path / "demo"), changelog_path=str(changelog)
    )

    calls = []
    monkeypatch.setattr(
        lt, "record_sync", lambda adapter, counts, errors=None: calls.append(
            (adapter, counts, errors)
        )
    )

    lt.sync_ledger_from_files()

    assert len(calls) == 1
    adapter, counts, errors = calls[0]
    assert adapter == "ledger_files"
    assert counts == {"demo": 1}
    assert errors is None


def test_sync_ledger_from_files_already_running_returns_stub_and_does_not_log(
    tmp_path, monkeypatch
) -> None:
    from contextlib import contextmanager

    _patch_conn(monkeypatch, tmp_path / "core.db")

    @contextmanager
    def _fake_lock(name):
        yield False

    monkeypatch.setattr(lt, "sync_lock", _fake_lock)
    calls = []
    monkeypatch.setattr(lt, "record_sync", lambda *a, **kw: calls.append(a))
    monkeypatch.setattr(
        lt,
        "sync_from_files",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("must not sync")),
    )

    result = lt.sync_ledger_from_files()
    assert result == {"status": "already_running", "projects": {}}
    assert calls == []
