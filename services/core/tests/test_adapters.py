"""Tests for signal adapters: isolation, todos, jira, changelog, git."""

from __future__ import annotations

import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

from sb_core.adapters import get_sync_states, run_adapter
from sb_core.store.db import connect
from sb_core.store.signals import search_signals

# ---------------------------------------------------------------------------
# Adapter framework: isolation — run_adapter now takes db_path, not conn
# ---------------------------------------------------------------------------


def test_failing_adapter_returns_error_without_raising(tmp_path: Path) -> None:
    db_path = tmp_path / "core.db"
    connect(db_path).close()  # initialise schema

    def bad_adapter(c: sqlite3.Connection) -> int:
        raise RuntimeError("deliberate failure")

    result = run_adapter("bad", bad_adapter, db_path)
    assert result.error is not None
    assert "deliberate failure" in result.error
    assert result.signal_count == 0


def test_failing_adapter_records_state(tmp_path: Path) -> None:
    db_path = tmp_path / "core.db"
    connect(db_path).close()

    def boom(c: sqlite3.Connection) -> int:
        raise ValueError("boom")

    run_adapter("exploding", boom, db_path)

    conn = connect(db_path)
    states = get_sync_states(conn)
    conn.close()
    bad = next((s for s in states if s["adapter"] == "exploding"), None)
    assert bad is not None
    assert bad["error"] is not None


def test_successful_adapter_records_count_and_clears_error(tmp_path: Path) -> None:
    db_path = tmp_path / "core.db"
    connect(db_path).close()

    def bad(c: sqlite3.Connection) -> int:
        raise RuntimeError("first fail")

    run_adapter("toggling", bad, db_path)

    def good(c: sqlite3.Connection) -> int:
        return 5

    result = run_adapter("toggling", good, db_path)
    assert result.signal_count == 5
    assert result.error is None

    conn = connect(db_path)
    states = get_sync_states(conn)
    conn.close()
    state = next(s for s in states if s["adapter"] == "toggling")
    assert state["signal_count"] == 5
    assert state["error"] is None


def test_one_adapter_failure_does_not_affect_others(tmp_path: Path) -> None:
    db_path = tmp_path / "core.db"
    connect(db_path).close()

    def fail(c: sqlite3.Connection) -> int:
        raise RuntimeError("fail")

    run_adapter("first", fail, db_path)
    run_adapter("second", lambda c: 3, db_path)

    conn = connect(db_path)
    states = {s["adapter"]: s for s in get_sync_states(conn)}
    conn.close()
    assert states["first"]["error"] is not None
    assert states["second"]["error"] is None
    assert states["second"]["signal_count"] == 3


# ---------------------------------------------------------------------------
# Issue 2: Timeout is truly bounded — no 'with executor' waiting
# ---------------------------------------------------------------------------


def test_adapter_timeout_is_bounded(tmp_path: Path) -> None:
    """run_adapter must return in ≈timeout seconds, not wait for the slow fn."""
    db_path = tmp_path / "core.db"
    connect(db_path).close()

    def slow(c: sqlite3.Connection) -> int:
        time.sleep(100)
        return 0

    timeout = 0.25
    t0 = time.monotonic()
    result = run_adapter("slow", slow, db_path, timeout=timeout)
    elapsed = time.monotonic() - t0

    assert result.error is not None, "Expected timeout error"
    assert elapsed < timeout + 1.0, (
        f"Elapsed {elapsed:.3f}s > timeout {timeout}s + 1.0s epsilon "
        "— run_adapter waited for the slow thread instead of returning promptly"
    )


def test_adapter_no_connection_crosses_thread_boundary(tmp_path: Path) -> None:
    """Adapter fn receives a connection opened inside the worker thread (no cross-thread sharing)."""
    db_path = tmp_path / "core.db"
    connect(db_path).close()

    thread_ids: list[int] = []

    def capture(c: sqlite3.Connection) -> int:
        import threading

        thread_ids.append(threading.current_thread().ident or 0)
        # Using the connection would raise if it was created in another thread
        # (check_same_thread=True is the SQLite default)
        c.execute("SELECT 1").fetchone()
        return 0

    import threading

    main_id = threading.current_thread().ident

    result = run_adapter("thread_check", capture, db_path)

    assert result.error is None, f"Unexpected error: {result.error}"
    assert thread_ids, "fn was never called"
    assert (
        thread_ids[0] != main_id
    ), "fn ran in main thread — should run in worker thread"


# ---------------------------------------------------------------------------
# Todos adapter
# ---------------------------------------------------------------------------


def _make_todos_conn() -> sqlite3.Connection:
    """In-memory todos DB with migrations applied."""
    from sb_todos.db import run_migrations as todos_mig

    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    todos_mig(c)
    return c


def test_todos_adapter_emits_task_signals(tmp_path: Path) -> None:
    todos_conn = _make_todos_conn()
    todos_conn.execute(
        "INSERT INTO todos (title, description, priority, tags, domain, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "My task",
            "do the thing",
            3,
            "[]",
            "work",
            "2026-01-01 00:00:00",
            "2026-01-01 00:00:00",
        ),
    )
    todos_conn.commit()

    core_conn = connect(tmp_path / "core.db")

    from sb_core.adapters.todos import run

    count = run(core_conn, todos_conn=todos_conn)

    assert count == 1
    signals = search_signals(core_conn, source="todos")
    assert len(signals) == 1
    assert signals[0].title == "My task"
    assert signals[0].kind == "task"
    assert signals[0].id > 0


def test_todos_adapter_is_idempotent(tmp_path: Path) -> None:
    todos_conn = _make_todos_conn()
    todos_conn.execute(
        "INSERT INTO todos (title, description, priority, tags, domain, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("Dup task", "", 2, "[]", "work", "2026-01-01 00:00:00", "2026-01-01 00:00:00"),
    )
    todos_conn.commit()

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.todos import run

    run(core_conn, todos_conn=todos_conn)
    run(core_conn, todos_conn=todos_conn)

    signals = search_signals(core_conn, source="todos")
    assert len(signals) == 1


# ---------------------------------------------------------------------------
# JIRA adapter
# ---------------------------------------------------------------------------


def _write_ticket(ticket_dir: Path, key: str, title: str) -> None:
    (ticket_dir / f"{key}.md").write_text(
        f"""# {key} — {title}

| Field | Value |
|-------|-------|
| **Key** | [{key}](https://example.com/{key}) |
| **Status** | Open |
| **Priority** | Medium |
| **Type** | Task |
| **Assignee** | Test User |
| **Reporter** | Test User |
| **Created** | 2026-01-01 |
| **Updated** | 2026-06-01 |

---

## Context

Ticket body here.
""",
        encoding="utf-8",
    )


def test_jira_adapter_emits_ticket_signals(tmp_path: Path) -> None:
    ticket_dir = tmp_path / "tickets"
    ticket_dir.mkdir()
    _write_ticket(ticket_dir, "CXP-999", "Test Ticket")

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.jira import run

    count = run(core_conn, tickets_dir=ticket_dir)

    assert count == 1
    signals = search_signals(core_conn, source="jira")
    assert len(signals) == 1
    assert "CXP-999" in signals[0].title
    assert signals[0].kind == "ticket"
    assert signals[0].id > 0


def test_jira_adapter_stores_raw_ref_for_file_path(tmp_path: Path) -> None:
    ticket_dir = tmp_path / "tickets"
    ticket_dir.mkdir()
    _write_ticket(ticket_dir, "CXP-1000", "Raw Ref Ticket")

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.jira import run

    run(core_conn, tickets_dir=ticket_dir)

    signals = search_signals(core_conn, source="jira")
    assert signals[0].raw_ref is not None


def test_jira_adapter_is_idempotent(tmp_path: Path) -> None:
    ticket_dir = tmp_path / "tickets"
    ticket_dir.mkdir()
    _write_ticket(ticket_dir, "CXP-42", "Idempotent Ticket")

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.jira import run

    run(core_conn, tickets_dir=ticket_dir)
    run(core_conn, tickets_dir=ticket_dir)

    signals = search_signals(core_conn, source="jira")
    assert len(signals) == 1


# ---------------------------------------------------------------------------
# Changelog adapter
# ---------------------------------------------------------------------------


def test_changelog_adapter_extracts_version_entries(tmp_path: Path) -> None:
    root = tmp_path / "myproject"
    root.mkdir()
    (root / "CHANGELOG.md").write_text(
        """\
# Changelog

## [1.2.0] - 2026-09-01

### Added
- New feature A
- New feature B

## [1.1.0] - 2026-08-01

### Fixed
- Bug fix C
""",
        encoding="utf-8",
    )

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.changelog import run

    count = run(core_conn, roots=[root])
    assert count >= 2

    signals = search_signals(core_conn, source="changelog")
    assert len(signals) >= 2
    titles = {s.title for s in signals}
    assert any("1.2.0" in t for t in titles)
    assert any("1.1.0" in t for t in titles)


def test_changelog_adapter_raw_ref_contains_path_and_line(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "CHANGELOG.md").write_text(
        """\
## v2.0.0
- Breaking change
""",
        encoding="utf-8",
    )

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.changelog import run

    run(core_conn, roots=[root])

    signals = search_signals(core_conn, source="changelog")
    assert signals
    assert all("CHANGELOG.md" in (s.raw_ref or "") for s in signals)
    for s in signals:
        parts = (s.raw_ref or "").rsplit(":", 1)
        assert len(parts) == 2, f"expected path:line, got {s.raw_ref!r}"
        assert parts[1].isdigit(), f"expected line number, got {parts[1]!r}"


def test_changelog_adapter_skips_roots_without_changelog(tmp_path: Path) -> None:
    root = tmp_path / "nochangelog"
    root.mkdir()

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.changelog import run

    count = run(core_conn, roots=[root])
    assert count == 0


def test_changelog_adapter_safe_with_empty_roots(tmp_path: Path) -> None:
    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.changelog import run

    count = run(core_conn, roots=[])
    assert count == 0


# ---------------------------------------------------------------------------
# Git adapter
# ---------------------------------------------------------------------------


def _init_repo_with_commit(path: Path, message: str = "Initial commit") -> None:
    path.mkdir(parents=True, exist_ok=True)
    # git init may return non-zero in sandboxed environments (hooks dir permission)
    subprocess.run(["git", "init", str(path)], capture_output=True)
    git_config = path / ".git" / "config"
    if not git_config.exists():
        pytest.skip("git init did not create .git/config (likely sandbox restriction)")
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
    )
    (path / "README.md").write_text("Hello", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(path), "add", "."], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", message],
        check=True,
        capture_output=True,
    )


def test_git_adapter_emits_commit_signals(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo_with_commit(repo, "feat: initial commit")

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.git import run

    count = run(core_conn, roots=[repo], since_days=30)

    assert count >= 1
    signals = search_signals(core_conn, source="git")
    assert len(signals) >= 1
    assert signals[0].kind == "commit"
    assert signals[0].id > 0


def test_git_adapter_includes_raw_ref_with_sha(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo_with_commit(repo, "sha check commit")

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.git import run

    run(core_conn, roots=[repo], since_days=30)

    signals = search_signals(core_conn, source="git")
    assert signals
    assert signals[0].raw_ref is not None
    assert any(c in (signals[0].raw_ref or "") for c in "0123456789abcdef")


def test_git_adapter_skips_non_git_roots(tmp_path: Path) -> None:
    not_git = tmp_path / "notgit"
    not_git.mkdir()

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.git import run

    count = run(core_conn, roots=[not_git], since_days=30)
    assert count == 0


def test_git_adapter_safe_with_empty_roots(tmp_path: Path) -> None:
    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.git import run

    count = run(core_conn, roots=[], since_days=30)
    assert count == 0


def test_git_adapter_filters_by_author(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo_with_commit(repo, "filtered commit")

    core_conn = connect(tmp_path / "core.db")
    from sb_core.adapters.git import run

    count = run(core_conn, roots=[repo], since_days=30, authors=["test@test.com"])
    assert count >= 1

    core_conn2 = connect(tmp_path / "core2.db")
    count2 = run(core_conn2, roots=[repo], since_days=30, authors=["other@other.com"])
    assert count2 == 0
