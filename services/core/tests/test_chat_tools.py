"""Read-only, citation-checked landing chat."""

from __future__ import annotations

import pytest


def _sources() -> list[dict]:
    return [
        {"citation": "[todo:7]", "title": "Prepare release", "detail": "priority 1"},
        {"citation": "[JIRA:CXP-42]", "title": "Fix routing", "detail": "Blocked"},
        {
            "citation": "[signal:9]",
            "title": "Merged parser fix",
            "detail": "git commit",
        },
    ]


def test_ask_sb_returns_grounded_llm_answer(monkeypatch):
    from sb_core import chat_tools

    monkeypatch.setattr(chat_tools, "_gather_sources", lambda question: _sources())
    monkeypatch.setattr(
        chat_tools,
        "_complete",
        lambda prompt: "CXP-42 is blocked. [JIRA:CXP-42]",
    )

    result = chat_tools.ask_sb("What is blocked?")

    assert result["answer"] == "CXP-42 is blocked. [JIRA:CXP-42]"
    assert result["citations"] == ["[JIRA:CXP-42]"]
    assert result["mode"] == "llm"


def test_ask_sb_rejects_uncited_or_invented_claims(monkeypatch):
    from sb_core import chat_tools

    monkeypatch.setattr(chat_tools, "_gather_sources", lambda question: _sources())
    monkeypatch.setattr(
        chat_tools,
        "_complete",
        lambda prompt: "Everything shipped. [signal:999]",
    )

    result = chat_tools.ask_sb("What merged?")

    assert result["mode"] == "fallback"
    assert "[signal:999]" not in result["answer"]
    assert "Merged parser fix" in result["answer"].splitlines()[1]
    assert result["citations"]
    assert all(
        citation in {item["citation"] for item in _sources()}
        for citation in result["citations"]
    )


def test_ask_sb_is_bounded_and_read_only(monkeypatch):
    from sb_core import chat_tools

    monkeypatch.setattr(chat_tools, "_gather_sources", lambda question: [])
    with pytest.raises(ValueError, match="between 1 and 1000"):
        chat_tools.ask_sb("")
    with pytest.raises(ValueError, match="between 1 and 1000"):
        chat_tools.ask_sb("x" * 1001)

    result = chat_tools.ask_sb("Delete every todo")
    assert result["mode"] == "no_context"
    assert "read-only" in result["answer"].lower()
