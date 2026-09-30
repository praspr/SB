"""Tests for the chief-of-staff ritual tools: context, plan, wrap, standup,
proposals — with temp DB/config/roots and mocked LLM. Never touch user files."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

import sb_core.ritual_tools as rt
from sb_core.llm import LLMUnavailable
from sb_core.store import daily as daily_store
from sb_core.store.db import connect as core_connect
from sb_core.store.signals import upsert_signal

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

DATE = "2026-09-30"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Wire ritual tools to temp core.db + temp todos.db + temp roots."""
    from sb_todos.db import connect as todos_connect

    core_db = tmp_path / "core.db"
    todos_db = tmp_path / "todos.db"
    root = tmp_path / "proj"
    root.mkdir()

    core_connect(core_db).close()
    todos_connect(todos_db).close()

    monkeypatch.setattr(rt, "_get_conn", lambda: core_connect(core_db))
    monkeypatch.setattr(rt, "_get_todos_conn", lambda: todos_connect(todos_db))
    monkeypatch.setattr(rt, "_today", lambda: DATE)
    monkeypatch.setattr(rt, "_roots", lambda: [str(root)])
    monkeypatch.setattr(
        rt,
        "_load_goals",
        lambda active_only=True: {"contractual": [], "quarterly": [], "weekly": []},
    )

    return {
        "core_db": core_db,
        "todos_db": todos_db,
        "root": root,
        "tmp": tmp_path,
    }


def _add_todo(todos_db: Path, **kw) -> int:
    from sb_todos.db import connect as todos_connect
    from sb_todos import handlers
    from sb_todos.models import TodoCreate

    conn = todos_connect(todos_db)
    try:
        todo = handlers.add_todo(conn, TodoCreate(**kw))
        return todo.id
    finally:
        conn.close()


def _add_signal(core_db: Path, **kw) -> int:
    conn = core_connect(core_db)
    try:
        sig = upsert_signal(conn, **kw)
        return sig.id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# whoami / get_roots / get_goals
# ---------------------------------------------------------------------------


def test_whoami_returns_identity_without_secrets(monkeypatch: pytest.MonkeyPatch):
    from sb_core.config import settings

    monkeypatch.setattr(settings, "identity_name", "Jane", raising=False)
    monkeypatch.setattr(settings, "identity_email", "jane@example.com", raising=False)

    result = rt.whoami()
    assert result["name"] == "Jane"
    assert result["email"] == "jane@example.com"
    blob = repr(result).lower()
    assert "token" not in blob
    assert "password" not in blob
    assert "secret" not in blob


def test_get_roots_returns_detailed_roots(monkeypatch: pytest.MonkeyPatch):
    from sb_core.config import settings

    monkeypatch.setattr(
        settings,
        "roots_detailed",
        [{"path": "/work/a", "label": "Primary", "domain": "work"}],
        raising=False,
    )
    result = rt.get_roots()
    roots = result["roots"] if isinstance(result, dict) else result
    assert roots[0]["path"] == "/work/a"
    assert roots[0]["label"] == "Primary"


def test_get_goals_missing_file_is_empty(tmp_path, monkeypatch):
    from sb_core.config import settings

    monkeypatch.setattr(settings, "goals_path", tmp_path / "none.yaml", raising=False)
    result = rt.get_goals()
    assert set(result) == {"contractual", "quarterly", "weekly"}
    assert all(result[c] == [] for c in result)


# ---------------------------------------------------------------------------
# plan_day / get_day
# ---------------------------------------------------------------------------


def test_plan_day_persists_and_ranks(env):
    _add_todo(env["todos_db"], title="Ship the release", priority=1)
    _add_todo(env["todos_db"], title="Tidy notes", priority=4)

    result = rt.plan_day()
    assert result["date"] == DATE
    assert "plan_md" in result and result["plan_md"]
    assert "Ship the release" in result["plan_md"]

    # Persisted exactly one row for the date
    conn = core_connect(env["core_db"])
    try:
        saved = daily_store.get_daily(conn, DATE)
        rows = conn.execute("SELECT COUNT(*) FROM sb_daily").fetchone()[0]
    finally:
        conn.close()
    assert saved is not None
    assert saved.get("plan_md")
    assert rows == 1


def test_plan_day_returns_cached_without_refresh(env):
    _add_todo(env["todos_db"], title="A task", priority=2)
    first = rt.plan_day()
    assert not first.get("cached")
    second = rt.plan_day()
    assert second.get("cached") is True
    refreshed = rt.plan_day(refresh=True)
    assert not refreshed.get("cached")


def test_plan_day_references_signal_evidence(env):
    _add_todo(env["todos_db"], title="Investigate outage", priority=1)
    _add_signal(
        env["core_db"],
        source="git",
        source_id="c1",
        kind="commit",
        occurred_at=f"{DATE}T09:00:00Z",
        title="fix: patch outage",
    )
    result = rt.plan_day()
    assert "[signal:" in result["plan_md"]


def test_get_day_missing_returns_stable_empty(env):
    result = rt.get_day()
    assert result["date"] == DATE
    assert result["plan_md"] is None
    assert result["wrap_md"] is None


def test_get_day_returns_persisted_plan(env):
    _add_todo(env["todos_db"], title="Persisted task", priority=1)
    rt.plan_day()
    result = rt.get_day()
    assert result["plan_md"]
    assert "Persisted task" in result["plan_md"]


# ---------------------------------------------------------------------------
# standup
# ---------------------------------------------------------------------------


def test_standup_returns_5_to_8_bullets(env):
    _add_todo(env["todos_db"], title="P1 work", priority=1)
    _add_todo(env["todos_db"], title="P2 work", priority=2)
    rt.plan_day()
    result = rt.standup()
    assert 5 <= len(result["bullets"]) <= 8
    assert all(isinstance(b, str) and b for b in result["bullets"])


def test_standup_is_deterministic_and_side_effect_free(env):
    _add_todo(env["todos_db"], title="Only task", priority=1)
    a = rt.standup()
    b = rt.standup()
    assert a["bullets"] == b["bullets"]
    # No daily row created by standup alone
    conn = core_connect(env["core_db"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM sb_daily").fetchone()[0] == 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# wrap_day
# ---------------------------------------------------------------------------


def test_wrap_dry_run_makes_no_mutations(env, monkeypatch):
    monkeypatch.setattr(
        rt, "_llm_complete", lambda prompt: (_ for _ in ()).throw(LLMUnavailable())
    )
    _add_signal(
        env["core_db"],
        source="git",
        source_id="c1",
        kind="commit",
        occurred_at=f"{DATE}T10:00:00Z",
        title="feat: shipped thing",
    )
    result = rt.wrap_day(dry_run=True)
    assert result["dry_run"] is True
    assert result["persisted"] is False
    assert result["wrap_md"]

    conn = core_connect(env["core_db"])
    try:
        assert daily_store.get_daily(conn, DATE) is None
        assert conn.execute("SELECT COUNT(*) FROM sb_proposals").fetchone()[0] == 0
    finally:
        conn.close()


def test_wrap_citations_are_all_valid(env, monkeypatch):
    monkeypatch.setattr(
        rt, "_llm_complete", lambda prompt: (_ for _ in ()).throw(LLMUnavailable())
    )
    sid = _add_signal(
        env["core_db"],
        source="git",
        source_id="c1",
        kind="commit",
        occurred_at=f"{DATE}T10:00:00Z",
        title="feat: shipped thing",
    )
    result = rt.wrap_day(dry_run=True)
    import re

    cited = {int(n) for n in re.findall(r"\[signal:(\d+)\]", result["wrap_md"])}
    assert cited  # at least one citation
    assert cited <= {sid}


def test_wrap_rejects_hallucinated_llm_citations(env, monkeypatch):
    sid = _add_signal(
        env["core_db"],
        source="git",
        source_id="c1",
        kind="commit",
        occurred_at=f"{DATE}T10:00:00Z",
        title="feat: real work",
    )

    # LLM returns a citation id that was never gathered
    monkeypatch.setattr(
        rt,
        "_llm_complete",
        lambda prompt: "- Did lots of things [signal:99999]\n",
    )
    result = rt.wrap_day(dry_run=True)
    import re

    cited = {int(n) for n in re.findall(r"\[signal:(\d+)\]", result["wrap_md"])}
    assert 99999 not in cited
    assert cited <= {sid}


def test_wrap_persists_and_queues_proposal_when_committed(env, monkeypatch):
    monkeypatch.setattr(
        rt, "_llm_complete", lambda prompt: (_ for _ in ()).throw(LLMUnavailable())
    )
    _add_signal(
        env["core_db"],
        source="git",
        source_id="c1",
        kind="commit",
        occurred_at=f"{DATE}T10:00:00Z",
        title="feat: shipped thing",
    )
    result = rt.wrap_day(dry_run=False)
    assert result["persisted"] is True

    conn = core_connect(env["core_db"])
    try:
        assert daily_store.get_daily(conn, DATE) is not None
        proposals = daily_store.list_proposals(conn, status="pending")
    finally:
        conn.close()
    assert any(p["type"] == "changelog" for p in proposals)


# ---------------------------------------------------------------------------
# proposals: list / reject / approve
# ---------------------------------------------------------------------------


def _make_proposal(core_db: Path, target_path: str, payload: str) -> int:
    conn = core_connect(core_db)
    try:
        p = daily_store.create_proposal(
            conn,
            kind="changelog",
            title="Add wrap entry",
            target_path=target_path,
            payload=payload,
            signal_refs=[1],
        )
        return p["id"]
    finally:
        conn.close()


def test_list_and_reject_proposal(env):
    pid = _make_proposal(
        env["core_db"], str(env["root"] / "CHANGELOG.md"), "## entry\n- did x\n"
    )
    listed = rt.list_proposals()
    assert any(p["id"] == pid for p in listed)

    rejected = rt.reject_proposal(pid)
    assert rejected["status"] == "rejected"
    assert rt.list_proposals(status="pending") == [] or all(
        p["id"] != pid for p in rt.list_proposals(status="pending")
    )


def test_approve_changelog_appends_and_marks_executed(env):
    target = env["root"] / "CHANGELOG.md"
    payload = "## 2026-09-30\n- Shipped thing [signal:1]\n"
    pid = _make_proposal(env["core_db"], str(target), payload)

    result = rt.approve_proposal(pid)
    assert result["status"] == "executed"
    assert target.exists()
    assert payload.strip() in target.read_text()

    conn = core_connect(env["core_db"])
    try:
        p = daily_store.get_proposal(conn, pid)
    finally:
        conn.close()
    assert p["status"] == "executed"


def test_approve_is_idempotent_when_payload_present(env):
    target = env["root"] / "CHANGELOG.md"
    payload = "## 2026-09-30\n- Shipped thing\n"
    target.write_text("# Changelog\n\n" + payload, encoding="utf-8")
    pid = _make_proposal(env["core_db"], str(target), payload)

    rt.approve_proposal(pid)
    # payload must appear exactly once
    assert target.read_text().count("Shipped thing") == 1


def test_approve_rejects_wrong_filename(env):
    bad = env["root"] / "notes.md"
    pid = _make_proposal(env["core_db"], str(bad), "- x\n")
    with pytest.raises(ValueError):
        rt.approve_proposal(pid)
    assert not bad.exists()
    conn = core_connect(env["core_db"])
    try:
        assert daily_store.get_proposal(conn, pid)["status"] == "pending"
    finally:
        conn.close()


def test_approve_rejects_target_outside_roots(env):
    outside = env["tmp"] / "outside"
    outside.mkdir()
    target = outside / "CHANGELOG.md"
    pid = _make_proposal(env["core_db"], str(target), "- x\n")
    with pytest.raises(ValueError):
        rt.approve_proposal(pid)
    assert not target.exists()


def test_approve_rejects_symlink_escape(env):
    outside = env["tmp"] / "escape"
    outside.mkdir()
    link = env["root"] / "link"
    link.symlink_to(outside, target_is_directory=True)
    target = link / "CHANGELOG.md"
    pid = _make_proposal(env["core_db"], str(target), "- x\n")
    with pytest.raises(ValueError):
        rt.approve_proposal(pid)
    assert not (outside / "CHANGELOG.md").exists()


def test_approve_rejects_oversized_payload(env):
    target = env["root"] / "CHANGELOG.md"
    huge = "- x\n" * 100000
    pid = _make_proposal(env["core_db"], str(target), huge)
    with pytest.raises(ValueError):
        rt.approve_proposal(pid)


def test_approve_never_writes_to_atlassian(env, monkeypatch):
    import sb_jira.atlassian_client as ac

    monkeypatch.setattr(
        ac,
        "fetch_all_assigned",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no Atlassian")),
    )
    target = env["root"] / "CHANGELOG.md"
    pid = _make_proposal(env["core_db"], str(target), "## e\n- did x\n")
    result = rt.approve_proposal(pid)
    assert result["status"] == "executed"


# ---------------------------------------------------------------------------
# No Atlassian side effects from plan/wrap/standup
# ---------------------------------------------------------------------------


def test_rituals_do_not_call_atlassian(env, monkeypatch):
    """Spy on the real Atlassian network boundary (httpx inside the client) and
    assert zero calls across plan/wrap/standup/approve."""
    import sb_jira.atlassian_client as ac

    calls: list[str] = []

    # Wrap the actual functions so the assertion is at a boundary that is truly
    # exercised: any invocation records a call and then fails loudly.
    for fn in ("fetch_all_assigned", "probe_reachable", "get_token"):
        if hasattr(ac, fn):
            monkeypatch.setattr(
                ac,
                fn,
                lambda *a, _n=fn, **k: (
                    calls.append(_n),
                    (_ for _ in ()).throw(AssertionError(f"Atlassian call: {_n}")),
                ),
            )
    monkeypatch.setattr(
        rt, "_llm_complete", lambda prompt: (_ for _ in ()).throw(LLMUnavailable())
    )

    _add_todo(env["todos_db"], title="Task", priority=1)
    rt.plan_day()
    wrapped = rt.wrap_day(dry_run=False)
    rt.standup()
    if wrapped["proposals"]:
        rt.approve_proposal(wrapped["proposals"][0]["id"])

    assert calls == []


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


RITUAL_TOOLS = {
    "plan_day",
    "wrap_day",
    "standup",
    "get_day",
    "list_proposals",
    "approve_proposal",
    "reject_proposal",
    "get_goals",
    "get_roots",
    "whoami",
}


def test_ritual_tools_registered():
    tools = asyncio.run(rt.mcp.list_tools())
    names = {t.name for t in tools}
    assert RITUAL_TOOLS <= names


# ---------------------------------------------------------------------------
# Item 1: proposal state machine (approve/reject transitions)
# ---------------------------------------------------------------------------


def test_reject_after_executed_raises(env):
    target = env["root"] / "CHANGELOG.md"
    pid = _make_proposal(env["core_db"], str(target), "## e\n- x\n")
    rt.approve_proposal(pid)  # -> executed
    with pytest.raises(ValueError):
        rt.reject_proposal(pid)


def test_approve_after_reject_raises(env):
    target = env["root"] / "CHANGELOG.md"
    pid = _make_proposal(env["core_db"], str(target), "## e\n- x\n")
    rt.reject_proposal(pid)  # -> rejected
    with pytest.raises(ValueError):
        rt.approve_proposal(pid)
    assert not target.exists()


def test_double_approve_raises_and_appends_once(env):
    target = env["root"] / "CHANGELOG.md"
    pid = _make_proposal(env["core_db"], str(target), "## once\n- only\n")
    rt.approve_proposal(pid)
    with pytest.raises(ValueError):
        rt.approve_proposal(pid)
    assert target.read_text().count("only") == 1


def test_reject_only_from_pending(env):
    target = env["root"] / "CHANGELOG.md"
    pid = _make_proposal(env["core_db"], str(target), "## e\n- x\n")
    first = rt.reject_proposal(pid)
    assert first["status"] == "rejected"
    with pytest.raises(ValueError):
        rt.reject_proposal(pid)


# ---------------------------------------------------------------------------
# Item 2/10: path safety — reject any symlink component (even within a root)
# ---------------------------------------------------------------------------


def test_approve_rejects_symlink_component_within_root(env):
    real_sub = env["root"] / "real"
    real_sub.mkdir()
    link = env["root"] / "link"
    link.symlink_to(real_sub, target_is_directory=True)
    target = link / "CHANGELOG.md"
    pid = _make_proposal(env["core_db"], str(target), "- x\n")
    with pytest.raises(ValueError):
        rt.approve_proposal(pid)
    assert not (real_sub / "CHANGELOG.md").exists()


def test_approve_rejects_symlinked_changelog_file(env):
    outside = env["tmp"] / "outfile"
    outside.mkdir()
    real_changelog = outside / "real.md"
    real_changelog.write_text("# real\n", encoding="utf-8")
    target = env["root"] / "CHANGELOG.md"
    target.symlink_to(real_changelog)
    pid = _make_proposal(env["core_db"], str(target), "- injected\n")
    with pytest.raises(ValueError):
        rt.approve_proposal(pid)
    assert "injected" not in real_changelog.read_text()


def test_approve_creates_parent_dir_under_root(env):
    target = env["root"] / "nested" / "CHANGELOG.md"
    pid = _make_proposal(env["core_db"], str(target), "## e\n- did\n")
    result = rt.approve_proposal(pid)
    assert result["status"] == "executed"
    assert target.exists()


# ---------------------------------------------------------------------------
# Item 3: citation validation
# ---------------------------------------------------------------------------


def test_wrap_no_signals_makes_no_factual_claims_and_skips_llm(env, monkeypatch):
    called = {"n": 0}

    def spy(prompt):
        called["n"] += 1
        return "- Something happened [signal:1]\n"

    monkeypatch.setattr(rt, "_llm_complete", spy)
    result = rt.wrap_day(dry_run=True)
    # No signals gathered -> LLM must not be called
    assert called["n"] == 0
    assert result["wrap_data"]["used_llm"] is False
    import re

    assert re.findall(r"\[signal:(\d+)\]", result["wrap_md"]) == []


def test_wrap_rejects_partially_cited_llm_output(env, monkeypatch):
    sid = _add_signal(
        env["core_db"],
        source="git",
        source_id="c1",
        kind="commit",
        occurred_at=f"{DATE}T10:00:00Z",
        title="feat: real",
    )
    # One bullet cited validly, one factual bullet with no citation.
    monkeypatch.setattr(
        rt,
        "_llm_complete",
        lambda prompt: f"- Did A [signal:{sid}]\n- Did B with no citation\n",
    )
    result = rt.wrap_day(dry_run=True)
    assert result["wrap_data"]["used_llm"] is False  # rejected -> fallback
    import re

    cited = {int(n) for n in re.findall(r"\[signal:(\d+)\]", result["wrap_md"])}
    assert cited <= {sid}


def test_wrap_accepts_fully_cited_llm_output(env, monkeypatch):
    sid = _add_signal(
        env["core_db"],
        source="git",
        source_id="c1",
        kind="commit",
        occurred_at=f"{DATE}T10:00:00Z",
        title="feat: real",
    )
    monkeypatch.setattr(
        rt, "_llm_complete", lambda prompt: f"- Shipped it [signal:{sid}]\n"
    )
    result = rt.wrap_day(dry_run=True)
    assert result["wrap_data"]["used_llm"] is True
    assert f"[signal:{sid}]" in result["wrap_md"]


# ---------------------------------------------------------------------------
# Item 6: refresh must not create a duplicate pending proposal
# ---------------------------------------------------------------------------


def test_wrap_refresh_does_not_duplicate_pending_proposal(env, monkeypatch):
    monkeypatch.setattr(
        rt, "_llm_complete", lambda prompt: (_ for _ in ()).throw(LLMUnavailable())
    )
    _add_signal(
        env["core_db"],
        source="git",
        source_id="c1",
        kind="commit",
        occurred_at=f"{DATE}T10:00:00Z",
        title="feat: thing",
    )
    rt.wrap_day(dry_run=False)
    rt.wrap_day(dry_run=False, refresh=True)

    conn = core_connect(env["core_db"])
    try:
        pending = daily_store.list_proposals(conn, status="pending")
    finally:
        conn.close()
    changelog = [p for p in pending if p["type"] == "changelog"]
    assert len(changelog) == 1


# ---------------------------------------------------------------------------
# Item 8: date validation + timezone-derived UTC range
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool", ["plan_day", "wrap_day", "standup", "get_day"])
def test_invalid_date_raises(env, tool):
    with pytest.raises(ValueError):
        getattr(rt, tool)(date="2026-13-40")


def test_wrap_gathers_signals_by_local_day_utc_range(env, monkeypatch):
    from datetime import timedelta, timezone

    # Local timezone UTC+05:30 -> local 2026-09-30 spans
    # 2026-09-29T18:30Z .. 2026-09-30T18:30Z
    monkeypatch.setattr(rt, "_tz", lambda: timezone(timedelta(hours=5, minutes=30)))
    monkeypatch.setattr(
        rt, "_llm_complete", lambda prompt: (_ for _ in ()).throw(LLMUnavailable())
    )
    sid = _add_signal(
        env["core_db"],
        source="git",
        source_id="early",
        kind="commit",
        occurred_at="2026-09-29T20:00:00Z",  # previous UTC day, same local day
        title="late-night commit",
    )
    result = rt.wrap_day(dry_run=True)
    import re

    cited = {int(n) for n in re.findall(r"\[signal:(\d+)\]", result["wrap_md"])}
    assert sid in cited


# ---------------------------------------------------------------------------
# Item 11: standup sources yesterday's wrap and avoids false blocker filler
# ---------------------------------------------------------------------------


def test_standup_uses_previous_day_wrap(env):
    from datetime import date, timedelta

    prev = (date.fromisoformat(DATE) - timedelta(days=1)).isoformat()
    conn = core_connect(env["core_db"])
    try:
        daily_store.save_wrap(
            conn, prev, "# Wrap prev\n- did stuff\n", {"signal_ids": []}
        )
    finally:
        conn.close()

    _add_todo(env["todos_db"], title="Task", priority=1)
    result = rt.standup()
    assert 5 <= len(result["bullets"]) <= 8
    joined = " ".join(result["bullets"]).lower()
    assert "yesterday" in joined


def test_standup_has_no_false_blocker_filler(env):
    _add_todo(env["todos_db"], title="Task", priority=1)
    result = rt.standup()
    # No fabricated "blockers: none" style filler.
    assert not any("blocker" in b.lower() for b in result["bullets"])
    assert 5 <= len(result["bullets"]) <= 8


# ---------------------------------------------------------------------------
# Item 7: todos MCP/ritual use fresh, self-owned connections
# ---------------------------------------------------------------------------


def test_ritual_uses_fresh_todos_connection_and_closes_it(env, monkeypatch):
    """_get_todos_conn returns a fresh connection each call and the ritual must
    close its own without affecting a caller's connection."""
    opened: list = []

    from sb_todos.db import connect as todos_connect

    def factory():
        c = todos_connect(env["todos_db"])
        opened.append(c)
        return c

    monkeypatch.setattr(rt, "_get_todos_conn", factory)
    _add_todo(env["todos_db"], title="Fresh conn task", priority=1)
    rt.plan_day()

    assert opened, "ritual did not obtain a todos connection"
    # Every connection the ritual opened must have been closed by the ritual.
    for c in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            c.execute("SELECT 1")


def test_todo_mcp_tools_use_fresh_connections(tmp_path, monkeypatch):
    """sb_todos MCP wrappers must not depend on a shared process-wide conn."""
    import sb_todos.mcp_tools as mt
    from sb_todos.db import connect as todos_connect
    from sb_todos.config import settings as todos_settings

    db = tmp_path / "todos.db"
    monkeypatch.setattr(todos_settings, "db_path", db, raising=False)

    created = mt.todo_add(title="Via MCP", priority=2)
    assert created["title"] == "Via MCP"
    listed = mt.todo_list(status="all")
    assert any(t["id"] == created["id"] for t in listed)

    # Data is actually persisted to the configured DB file (fresh connection).
    verify = todos_connect(db)
    try:
        rows = verify.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
    finally:
        verify.close()
    assert rows >= 1
