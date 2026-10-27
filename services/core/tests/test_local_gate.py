"""Tests for the write-tool access gate (M5): local token + middleware."""

from __future__ import annotations

from pathlib import Path

import pytest

from sb_core import local_token
from sb_core.local_gate import WRITE_TOOLS, WriteToolGate, LocalTokenError


# ---------------------------------------------------------------------------
# local_token
# ---------------------------------------------------------------------------


def test_token_is_persisted_stable_and_0600(tmp_path: Path) -> None:
    path = tmp_path / "local_token"
    first = local_token.ensure_token(path)
    second = local_token.ensure_token(path)
    assert first == second
    assert len(first) > 20
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_token_matches_and_rejects(tmp_path: Path) -> None:
    path = tmp_path / "local_token"
    token = local_token.ensure_token(path)
    assert local_token.token_matches(token, path) is True
    assert local_token.token_matches("wrong", path) is False
    assert local_token.token_matches(None, path) is False
    assert local_token.token_matches("", path) is False


# ---------------------------------------------------------------------------
# WriteToolGate middleware
# ---------------------------------------------------------------------------


class _Msg:
    def __init__(self, name: str) -> None:
        self.name = name


class _Ctx:
    def __init__(self, name: str) -> None:
        self.message = _Msg(name)


async def _passthrough(_ctx):
    return "ran"


@pytest.mark.asyncio
async def test_read_tool_is_never_gated(monkeypatch) -> None:
    gate = WriteToolGate()
    # Even with enforcement on and no token, a non-write tool must pass.
    monkeypatch.setattr("sb_core.local_gate._require_enabled", lambda: True)
    monkeypatch.setattr("sb_core.local_gate._extract_token", lambda: None)
    result = await gate.on_call_tool(_Ctx("ledger_search"), _passthrough)
    assert result == "ran"


@pytest.mark.asyncio
async def test_write_tool_observe_mode_allows_without_token(monkeypatch) -> None:
    gate = WriteToolGate()
    monkeypatch.setattr("sb_core.local_gate._require_enabled", lambda: False)
    monkeypatch.setattr("sb_core.local_gate._extract_token", lambda: None)
    # Observe-only: proceeds despite missing token.
    result = await gate.on_call_tool(_Ctx("ledger_log"), _passthrough)
    assert result == "ran"


@pytest.mark.asyncio
async def test_write_tool_enforced_rejects_without_token(monkeypatch) -> None:
    gate = WriteToolGate()
    monkeypatch.setattr("sb_core.local_gate._require_enabled", lambda: True)
    monkeypatch.setattr("sb_core.local_gate._extract_token", lambda: None)
    with pytest.raises(LocalTokenError):
        await gate.on_call_tool(_Ctx("todo_add"), _passthrough)


@pytest.mark.asyncio
async def test_write_tool_enforced_rejects_wrong_token(monkeypatch) -> None:
    gate = WriteToolGate()
    monkeypatch.setattr("sb_core.local_gate._require_enabled", lambda: True)
    monkeypatch.setattr("sb_core.local_gate._extract_token", lambda: "bogus")
    monkeypatch.setattr("sb_core.local_gate.local_token.token_matches", lambda c: False)
    with pytest.raises(LocalTokenError):
        await gate.on_call_tool(_Ctx("webex_post_message"), _passthrough)


@pytest.mark.asyncio
async def test_write_tool_enforced_allows_with_valid_token(monkeypatch) -> None:
    gate = WriteToolGate()
    monkeypatch.setattr("sb_core.local_gate._require_enabled", lambda: True)
    monkeypatch.setattr("sb_core.local_gate._extract_token", lambda: "good")
    monkeypatch.setattr("sb_core.local_gate.local_token.token_matches", lambda c: True)
    result = await gate.on_call_tool(_Ctx("todo_complete"), _passthrough)
    assert result == "ran"


def test_write_tools_set_is_nonempty_and_includes_key_mutators() -> None:
    for name in ("todo_add", "ledger_log", "webex_post_message", "track_jira"):
        assert name in WRITE_TOOLS
