"""Arg parsing + mocked HTTP call tests for `sb log`."""

from __future__ import annotations

import pytest

import sb_cli.__main__ as main_module
from sb_cli.commands.log import _parse_ref


def test_parse_ref_value_only() -> None:
    assert _parse_ref("todo=123") == {"kind": "todo", "value": "123"}


def test_parse_ref_with_url() -> None:
    result = _parse_ref("pr=45:https://github.com/org/repo/pull/45")
    assert result == {
        "kind": "pr",
        "value": "45",
        "url": "https://github.com/org/repo/pull/45",
    }


def test_parse_ref_requires_equals() -> None:
    with pytest.raises(ValueError):
        _parse_ref("no-equals-sign")


def test_log_parser_requires_project(capsys) -> None:
    parser = main_module.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["log", "a summary"])


def test_log_command_calls_ledger_log_tool(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            self.endpoint = endpoint

        def call_tool(self, name, arguments=None):
            calls.append((name, arguments or {}))
            return {"id": 1, "ts": "2026-09-30T00:00:00Z", "was_new": True, "persisted_to_file": False}

    monkeypatch.setattr("sb_cli.commands.log.McpClient", FakeClient)
    monkeypatch.setenv("SB_AGENT", "test-agent")

    exit_code = main_module.main(["--quiet", "log", "hello world", "--project", "sb"])

    assert exit_code == 0
    assert len(calls) == 1
    name, arguments = calls[0]
    assert name == "ledger_log"
    assert arguments["summary"] == "hello world"
    assert arguments["project"] == "sb"
    assert arguments["agent"] == "test-agent"
    assert arguments["source_harness"] == "sb-log-cli"


def test_log_command_idempotent_no_op_exits_zero(monkeypatch, capsys) -> None:
    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            return {"id": 1, "ts": "2026-09-30T00:00:00Z", "was_new": False, "persisted_to_file": False}

    monkeypatch.setattr("sb_cli.commands.log.McpClient", FakeClient)

    exit_code = main_module.main(["log", "dup summary", "--project", "sb"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "already recorded" in out


def test_log_command_transport_failure_exits_nonzero(monkeypatch, capsys) -> None:
    from sb_cli.client import McpTransportError

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            raise McpTransportError("could not reach sb-core")

    monkeypatch.setattr("sb_cli.commands.log.McpClient", FakeClient)

    exit_code = main_module.main(["log", "unreachable", "--project", "sb"])
    err = capsys.readouterr().err
    assert exit_code == 1
    assert "could not reach" in err


def test_log_command_with_ref_flag(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, endpoint: str) -> None:
            pass

        def call_tool(self, name, arguments=None):
            calls.append(arguments or {})
            return {"id": 2, "ts": "2026-09-30T00:00:00Z", "was_new": True, "persisted_to_file": True}

    monkeypatch.setattr("sb_cli.commands.log.McpClient", FakeClient)

    main_module.main(
        [
            "--quiet",
            "log",
            "linked a pr",
            "--project",
            "sb",
            "--ref",
            "pr=45:https://github.com/org/repo/pull/45",
        ]
    )
    assert calls[0]["refs"] == [
        {"kind": "pr", "value": "45", "url": "https://github.com/org/repo/pull/45"}
    ]
