"""Arg parsing + mocked HTTP call tests for `sb context`."""

from __future__ import annotations

import sb_cli.__main__ as main_module
from sb_cli.commands.context import _parse_since


def test_parse_since_hours() -> None:
    result = _parse_since("48h")
    assert result.endswith("Z")
    assert "T" in result


def test_parse_since_days() -> None:
    result = _parse_since("2d")
    assert result.endswith("Z")


def test_parse_since_passthrough_iso() -> None:
    assert _parse_since("2026-01-01T00:00:00Z") == "2026-01-01T00:00:00Z"


def test_context_command_calls_ledger_context_tool(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            calls.append((name, arguments or {}))
            return {"entries": [], "open_threads": [], "tracked_refs": []}

    monkeypatch.setattr("sb_cli.commands.context.McpClient", FakeClient)

    exit_code = main_module.main(["--quiet", "context", "--project", "sb", "--since", "48h"])

    assert exit_code == 0
    name, arguments = calls[0]
    assert name == "ledger_context"
    assert arguments["project"] == "sb"
    assert arguments["limit"] == 30


def test_context_command_prints_entries(monkeypatch, capsys) -> None:
    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            return {
                "entries": [
                    {"id": 1, "ts": "2026-09-30T00:00:00Z", "action_verb": "Shipped", "summary": "thing"}
                ],
                "open_threads": [],
                "tracked_refs": [],
            }

    monkeypatch.setattr("sb_cli.commands.context.McpClient", FakeClient)

    main_module.main(["context", "--project", "sb"])
    out = capsys.readouterr().out
    assert "Shipped" in out
    assert "thing" in out


def test_context_command_json_output(monkeypatch, capsys) -> None:
    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            return {"entries": [], "open_threads": [], "tracked_refs": []}

    monkeypatch.setattr("sb_cli.commands.context.McpClient", FakeClient)

    main_module.main(["--json", "context", "--project", "sb"])
    out = capsys.readouterr().out
    assert '"entries"' in out


def test_context_command_transport_failure(monkeypatch, capsys) -> None:
    from sb_cli.client import McpTransportError

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            raise McpTransportError("down")

    monkeypatch.setattr("sb_cli.commands.context.McpClient", FakeClient)

    exit_code = main_module.main(["context", "--project", "sb"])
    assert exit_code == 1
