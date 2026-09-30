"""Arg parsing + mocked HTTP call tests for `sb projects`."""

from __future__ import annotations

import sb_cli.__main__ as main_module


def test_projects_list_calls_ledger_projects_tool(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            calls.append((name, arguments or {}))
            return [{"project": "sb", "root_path": "/x", "changelog_path": "/x/CHANGELOG.md", "sync_mode": "dual"}]

    monkeypatch.setattr("sb_cli.commands.projects.McpClient", FakeClient)

    exit_code = main_module.main(["--quiet", "projects", "list"])

    assert exit_code == 0
    name, arguments = calls[0]
    assert name == "ledger_projects"
    assert arguments == {}


def test_projects_list_prints_rows(monkeypatch, capsys) -> None:
    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            return [{"project": "sb", "root_path": "/x", "changelog_path": "/x/CHANGELOG.md", "sync_mode": "dual"}]

    monkeypatch.setattr("sb_cli.commands.projects.McpClient", FakeClient)
    main_module.main(["projects", "list"])
    out = capsys.readouterr().out
    assert "sb" in out
    assert "/x/CHANGELOG.md" in out


def test_projects_enroll_calls_register_tool(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            calls.append((name, arguments or {}))
            return {"project": "demo", "root_path": "/abs/path", "changelog_path": "/abs/path/CHANGELOG.md", "sync_mode": "dual"}

    monkeypatch.setattr("sb_cli.commands.projects.McpClient", FakeClient)

    exit_code = main_module.main(
        ["--quiet", "projects", "enroll", "--project", "demo", "--path", "/abs/path"]
    )

    assert exit_code == 0
    name, arguments = calls[0]
    assert name == "ledger_register_project"
    assert arguments["project"] == "demo"
    assert arguments["root_path"] == "/abs/path"
    assert arguments["sync_mode"] == "dual"


def test_projects_enroll_accepts_custom_changelog_and_sync_mode(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            calls.append(arguments or {})
            return {"project": "demo", "root_path": "/abs", "changelog_path": "/other/CHANGELOG.md", "sync_mode": "sqlite-only"}

    monkeypatch.setattr("sb_cli.commands.projects.McpClient", FakeClient)

    main_module.main(
        [
            "--quiet",
            "projects",
            "enroll",
            "--project",
            "demo",
            "--path",
            "/abs",
            "--changelog",
            "/other/CHANGELOG.md",
            "--sync-mode",
            "sqlite-only",
        ]
    )
    assert calls[0]["changelog_path"] == "/other/CHANGELOG.md"
    assert calls[0]["sync_mode"] == "sqlite-only"


def test_projects_requires_subcommand() -> None:
    import argparse

    import pytest

    parser = main_module.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["projects"])


def test_projects_enroll_transport_failure_exits_nonzero(monkeypatch) -> None:
    from sb_cli.client import McpTransportError

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            raise McpTransportError("down")

    monkeypatch.setattr("sb_cli.commands.projects.McpClient", FakeClient)
    exit_code = main_module.main(["projects", "enroll", "--project", "x", "--path", "/y"])
    assert exit_code == 1
