"""ask_sb ledger-citation coverage: [ledger:<id>] validates and unsupported
ledger citations are stripped/fall back, matching existing signal/todo/jira/
webex citation behavior."""

from __future__ import annotations


def _sources_with_ledger() -> list[dict]:
    return [
        {"citation": "[todo:7]", "title": "Prepare release", "detail": "priority 1"},
        {
            "citation": "[ledger:5]",
            "title": "Shipped the reports backend",
            "detail": "sb/core; 2026-09-30T09:00:00Z",
        },
        {
            "citation": "[ledger:6]",
            "title": "Debugged APISIX 401",
            "detail": "sb/core; 2026-09-29T09:00:00Z",
        },
    ]


def test_ask_sb_validates_ledger_citation(monkeypatch):
    from sb_core import chat_tools

    monkeypatch.setattr(chat_tools, "_gather_sources", lambda question: _sources_with_ledger())
    monkeypatch.setattr(
        chat_tools,
        "_complete",
        lambda prompt: "You shipped the reports backend. [ledger:5]",
    )

    result = chat_tools.ask_sb("What did I ship?")

    assert result["mode"] == "llm"
    assert result["citations"] == ["[ledger:5]"]


def test_ask_sb_rejects_hallucinated_ledger_citation(monkeypatch):
    from sb_core import chat_tools

    monkeypatch.setattr(chat_tools, "_gather_sources", lambda question: _sources_with_ledger())
    monkeypatch.setattr(
        chat_tools,
        "_complete",
        lambda prompt: "You shipped everything. [ledger:999999]",
    )

    result = chat_tools.ask_sb("What did I ship?")

    assert result["mode"] == "fallback"
    assert "[ledger:999999]" not in result["answer"]
    assert result["citations"]
    assert all(
        citation in {item["citation"] for item in _sources_with_ledger()}
        for citation in result["citations"]
    )


def test_ask_sb_accepts_mixed_ledger_and_todo_citations(monkeypatch):
    from sb_core import chat_tools

    monkeypatch.setattr(chat_tools, "_gather_sources", lambda question: _sources_with_ledger())
    monkeypatch.setattr(
        chat_tools,
        "_complete",
        lambda prompt: "Prepare release is todo:7 and ledger:6 covers the debug. [todo:7] [ledger:6]",
    )

    result = chat_tools.ask_sb("What is going on?")

    assert result["mode"] == "llm"
    assert set(result["citations"]) == {"[todo:7]", "[ledger:6]"}


def test_gather_sources_includes_ledger_entries(monkeypatch):
    """Integration-lite: _gather_sources actually queries search_ledger and
    surfaces [ledger:<id>] citations without touching real todos/JIRA/webex
    stores (each is monkeypatched to a fixed fake payload)."""
    from sb_core import chat_tools

    fake_entries = [
        {
            "id": 42,
            "action_verb": "Shipped",
            "summary": "the reports backend",
            "project": "sb",
            "scope": "core",
            "ts": "2026-09-30T09:00:00Z",
        }
    ]

    class _NullConn:
        def close(self):
            pass

    monkeypatch.setattr(
        "sb_core.store.ledger.search_ledger", lambda conn, limit=50: fake_entries
    )
    monkeypatch.setattr(
        "sb_core.store.signals.search_signals", lambda conn, limit=50: []
    )
    monkeypatch.setattr("sb_core.webex_store.list_messages", lambda conn: [])
    monkeypatch.setattr("sb_core.webex_store.list_meetings", lambda conn: [])
    monkeypatch.setattr(
        "sb_todos.handlers.list_todos", lambda conn, status="open", limit=50: []
    )
    monkeypatch.setattr("sb_todos.db.connect", lambda db_path: _NullConn())
    monkeypatch.setattr("sb_core.store.db.connect", lambda db_path: _NullConn())
    monkeypatch.setattr("sb_jira.file_store.load_all", lambda: [])

    sources = chat_tools._gather_sources("What did I ship?")
    ledger_sources = [s for s in sources if s["citation"].startswith("[ledger:")]
    assert len(ledger_sources) == 1
    assert ledger_sources[0]["citation"] == "[ledger:42]"
    assert "the reports backend" in ledger_sources[0]["title"]
