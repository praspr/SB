"""Tests for url_hints.py: classify pasted URLs into kind + extracted fields."""

from __future__ import annotations

import asyncio

import sb_core.url_hints as uh
from sb_core.url_hints import parse_url_hint


def test_url_hints_tool_is_registered_and_mounted() -> None:
    names = {t.name for t in asyncio.run(uh.mcp.list_tools())}
    assert "parse_url_hint" in names

    from sb_core.mcp_app import mcp as parent

    mounted = {t.name for t in asyncio.run(parent.list_tools())}
    assert "parse_url_hint" in mounted


def test_jira_browse_link() -> None:
    result = parse_url_hint("https://cisco-cxe.atlassian.net/browse/CXP-54493")
    assert result["kind"] == "jira"
    assert result["extracted"]["key"] == "CXP-54493"
    assert result["extracted"]["site"] == "cisco-cxe.atlassian.net"
    assert result["suggested_action"] == "track_jira"


def test_jira_browse_link_with_trailing_slash() -> None:
    result = parse_url_hint("https://cisco-cxe.atlassian.net/browse/CXP-1/")
    assert result["kind"] == "jira"
    assert result["extracted"]["key"] == "CXP-1"


def test_webex_app_deep_link() -> None:
    result = parse_url_hint("webexteams://im?space=abc123&other=1")
    assert result["kind"] == "webex"
    assert result["extracted"]["space_id"] == "abc123"
    assert result["suggested_action"] == "open_space"


def test_webex_web_space_link() -> None:
    result = parse_url_hint("https://web.webex.com/space/abc-def-123")
    assert result["kind"] == "webex"
    assert result["extracted"]["space_id"] == "abc-def-123"


def test_github_pull_request_link() -> None:
    result = parse_url_hint("https://github.com/CXEPI/cxp-priority-bugs-ai/pull/50")
    assert result["kind"] == "github"
    assert result["extracted"]["repo"] == "CXEPI/cxp-priority-bugs-ai"
    assert result["extracted"]["pr_number"] == 50
    assert result["suggested_action"] == "attach_as_ref"


def test_file_uri() -> None:
    result = parse_url_hint("file:///Users/praspr/Documents/code_home/sb/CHANGELOG.md")
    assert result["kind"] == "file"
    assert result["extracted"]["path"] == "/Users/praspr/Documents/code_home/sb/CHANGELOG.md"
    assert result["suggested_action"] == "attach_as_ref"


def test_generic_fallback() -> None:
    result = parse_url_hint("https://example.com/whatever")
    assert result["kind"] == "generic"
    assert result["suggested_action"] == "attach_as_ref"
    assert result["extracted"]["url"] == "https://example.com/whatever"


def test_blank_url_is_generic() -> None:
    result = parse_url_hint("")
    assert result["kind"] == "generic"


def test_whitespace_is_stripped() -> None:
    result = parse_url_hint("  https://cisco-cxe.atlassian.net/browse/CXP-1  ")
    assert result["kind"] == "jira"
    assert result["extracted"]["key"] == "CXP-1"
