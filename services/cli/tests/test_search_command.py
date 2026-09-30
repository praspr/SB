"""Arg parsing + mocked HTTP call tests for `sb search`."""

from __future__ import annotations

import sb_cli.__main__ as main_module


def test_search_command_calls_ledger_search_tool(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            calls.append((name, arguments or {}))
            return []

    monkeypatch.setattr("sb_cli.commands.search.McpClient", FakeClient)

    exit_code = main_module.main(
        ["--quiet", "search", "APISIX", "--project", "sb", "--verb", "Debugged", "--limit", "10"]
    )

    assert exit_code == 0
    name, arguments = calls[0]
    assert name == "ledger_search"
    assert arguments["q"] == "APISIX"
    assert arguments["project"] == "sb"
    assert arguments["verb"] == "Debugged"
    assert arguments["limit"] == 10


def test_search_command_without_query(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            calls.append(arguments or {})
            return []

    monkeypatch.setattr("sb_cli.commands.search.McpClient", FakeClient)
    main_module.main(["--quiet", "search", "--project", "sb"])
    assert calls[0]["q"] is None


def test_search_command_prints_entries(monkeypatch, capsys) -> None:
    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            return [
                {"id": 5, "ts": "2026-09-30T00:00:00Z", "action_verb": "Fixed", "summary": "the bug"}
            ]

    monkeypatch.setattr("sb_cli.commands.search.McpClient", FakeClient)
    main_module.main(["search", "bug"])
    out = capsys.readouterr().out
    assert "Fixed" in out
    assert "the bug" in out


def test_search_command_since_is_normalized(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            calls.append(arguments or {})
            return []

    monkeypatch.setattr("sb_cli.commands.search.McpClient", FakeClient)
    main_module.main(["--quiet", "search", "x", "--since", "48h"])
    assert calls[0]["since"].endswith("Z")


def test_search_command_transport_failure_exits_nonzero(monkeypatch) -> None:
    from sb_cli.client import McpTransportError

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            raise McpTransportError("down")

    monkeypatch.setattr("sb_cli.commands.search.McpClient", FakeClient)
    exit_code = main_module.main(["search", "x"])
    assert exit_code == 1
