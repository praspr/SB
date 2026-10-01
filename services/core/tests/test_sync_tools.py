"""Tests for sync MCP tool registrations and basic behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from sb_core.adapters import AdapterResult
from sb_core.store.db import connect
from sb_core.store.signals import upsert_signal

# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def test_sync_tools_are_registered_in_mcp() -> None:
    """sync_adapters, sync_status, search_signals must appear in the MCP tool list."""
    from sb_core.mcp_app import mcp as parent
    from sb_core.sync_tools import mcp as sync_mcp

    for server in (sync_mcp, parent):
        tools = asyncio.run(server.list_tools())
        names = {t.name for t in tools}
        assert "sync_adapters" in names
        assert "sync_status" in names
        assert "search_signals" in names


# ---------------------------------------------------------------------------
# search_signals
# ---------------------------------------------------------------------------


def test_search_signals_returns_empty_list_on_fresh_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st

    # Patch _get_conn to return a fresh connection to the test DB each call
    monkeypatch.setattr(st, "_get_conn", lambda: connect(tmp_path / "core.db"))

    result = st.search_signals()
    assert isinstance(result, list)
    assert result == []


def test_search_signals_returns_dicts_with_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st

    db_path = tmp_path / "core.db"
    monkeypatch.setattr(st, "_get_conn", lambda: connect(db_path))

    # Write data with a direct connection
    wc = connect(db_path)
    upsert_signal(
        wc,
        source="todos",
        source_id="99",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="MCP tool test signal",
    )
    wc.close()

    results = st.search_signals()
    assert len(results) == 1
    assert isinstance(results[0], dict)
    assert results[0]["id"] > 0
    assert results[0]["source"] == "todos"
    assert results[0]["title"] == "MCP tool test signal"


def test_search_signals_q_filter_works_via_mcp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st

    db_path = tmp_path / "core.db"
    monkeypatch.setattr(st, "_get_conn", lambda: connect(db_path))

    wc = connect(db_path)
    upsert_signal(
        wc,
        source="t",
        source_id="a",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="Alpha task",
    )
    upsert_signal(
        wc,
        source="t",
        source_id="b",
        kind="task",
        occurred_at="2026-01-01T00:00:00Z",
        title="Beta task",
    )
    wc.close()

    results = st.search_signals(q="Alpha")
    assert len(results) == 1
    assert results[0]["title"] == "Alpha task"


# ---------------------------------------------------------------------------
# sync_status
# ---------------------------------------------------------------------------


def test_sync_status_returns_empty_states_on_fresh_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st

    monkeypatch.setattr(st, "_get_conn", lambda: connect(tmp_path / "core.db"))

    result = st.sync_status()
    assert "states" in result
    assert isinstance(result["states"], list)
    assert result["states"] == []


def test_sync_status_shows_states_after_adapter_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st
    from sb_core.adapters import run_adapter

    db_path = tmp_path / "core.db"
    monkeypatch.setattr(st, "_get_conn", lambda: connect(db_path))

    # Inject state via thread-based run_adapter (uses db_path directly)
    run_adapter("mock_adapter", lambda c: 7, db_path)

    result = st.sync_status()
    states = {s["adapter"]: s for s in result["states"]}
    assert "mock_adapter" in states
    assert states["mock_adapter"]["signal_count"] == 7
    assert states["mock_adapter"]["error"] is None


# ---------------------------------------------------------------------------
# sync_adapters — patch _run_one_adapter to avoid subprocess spawning in tests
# ---------------------------------------------------------------------------


def test_sync_adapters_returns_per_adapter_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st

    db_path = tmp_path / "core.db"
    monkeypatch.setattr(st, "_get_conn", lambda: connect(db_path))
    # Patch the production subprocess runner to a simple mock
    monkeypatch.setattr(
        st,
        "_run_one_adapter",
        lambda name, db_path, config: AdapterResult(
            adapter=name, signal_count=0, error=None
        ),
    )

    result = st.sync_adapters(adapters=["changelog", "git"])
    assert "adapters" in result
    assert "changelog" in result["adapters"]
    assert "git" in result["adapters"]
    assert result["adapters"]["changelog"]["error"] is None
    assert result["adapters"]["git"]["error"] is None


def test_sync_adapters_unknown_adapter_does_not_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st

    monkeypatch.setattr(st, "_get_conn", lambda: connect(tmp_path / "core.db"))
    monkeypatch.setattr(
        st,
        "_run_one_adapter",
        lambda name, db_path, config: AdapterResult(
            adapter=name, signal_count=0, error=None
        ),
    )

    result = st.sync_adapters(adapters=["nonexistent"])
    assert "nonexistent" in result["adapters"]
    assert result["adapters"]["nonexistent"]["error"] is not None


def test_sync_adapters_isolation_one_fails_others_succeed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If one adapter errors, others must still run."""
    import sb_core.sync_tools as st

    monkeypatch.setattr(st, "_get_conn", lambda: connect(tmp_path / "core.db"))

    def patched_runner(name, db_path, config):
        if name == "changelog":
            return AdapterResult(adapter=name, error="synthetic failure")
        return AdapterResult(adapter=name, signal_count=0, error=None)

    monkeypatch.setattr(st, "_run_one_adapter", patched_runner)

    result = st.sync_adapters(adapters=["changelog", "git"])
    assert result["adapters"]["changelog"]["error"] is not None
    assert result["adapters"]["git"]["error"] is None


# ---------------------------------------------------------------------------
# sync_adapters — lock + record_sync wiring (phase 2j)
# ---------------------------------------------------------------------------


def test_sync_adapters_records_sync_with_aggregated_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st

    monkeypatch.setattr(st, "_get_conn", lambda: connect(tmp_path / "core.db"))
    monkeypatch.setattr(
        st,
        "_run_one_adapter",
        lambda name, db_path, config: AdapterResult(
            adapter=name, signal_count=3, error=None
        ),
    )

    calls = []
    monkeypatch.setattr(
        st, "record_sync", lambda adapter, counts, errors=None: calls.append(
            (adapter, counts, errors)
        )
    )

    st.sync_adapters(adapters=["changelog", "git"])

    assert len(calls) == 1
    adapter, counts, errors = calls[0]
    assert adapter == "adapters"
    assert counts == {"changelog": 3, "git": 3}
    assert errors is None


def test_sync_adapters_record_sync_includes_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st

    monkeypatch.setattr(st, "_get_conn", lambda: connect(tmp_path / "core.db"))

    def patched_runner(name, db_path, config):
        if name == "changelog":
            return AdapterResult(adapter=name, error="synthetic failure")
        return AdapterResult(adapter=name, signal_count=0, error=None)

    monkeypatch.setattr(st, "_run_one_adapter", patched_runner)

    calls = []
    monkeypatch.setattr(
        st, "record_sync", lambda adapter, counts, errors=None: calls.append(
            (adapter, counts, errors)
        )
    )

    st.sync_adapters(adapters=["changelog", "git"])

    assert len(calls) == 1
    _, _, errors = calls[0]
    assert errors == ["changelog: synthetic failure"]


def test_sync_adapters_already_running_returns_stub_and_does_not_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sb_core.sync_tools as st
    from contextlib import contextmanager

    monkeypatch.setattr(st, "_get_conn", lambda: connect(tmp_path / "core.db"))

    @contextmanager
    def _fake_lock(name):
        yield False

    monkeypatch.setattr(st, "sync_lock", _fake_lock)

    calls = []
    monkeypatch.setattr(
        st, "record_sync", lambda *a, **kw: calls.append((a, kw))
    )
    monkeypatch.setattr(
        st,
        "_run_one_adapter",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    result = st.sync_adapters(adapters=["changelog"])
    assert result == {"status": "already_running", "adapters": {}}
    assert calls == []
