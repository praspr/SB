"""Adapter framework: isolated execution, bounded timeout, status recording.

Two execution paths:
* ``run_adapter(name, fn, db_path, timeout)`` — thread-based.  The worker
  opens its own SQLite connection (no cross-thread sharing); ``t.join(timeout)``
  without a ``with`` block so the call returns promptly on timeout even though
  the daemon thread may still be running in the background.
  Used for unit tests and the test timeout-bound proof.

* ``run_adapter_by_name(name, db_path, config, timeout)`` — subprocess-based.
  A fresh process is spawned (macOS ``spawn`` safe), it opens its own
  SQLite connection, dispatches by name, and is ``terminate()``-ed on timeout.
  Used by the production ``sync_adapters`` MCP tool.
"""

from __future__ import annotations

import logging
import multiprocessing
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    adapter: str
    signal_count: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record_state(
    conn: sqlite3.Connection,
    *,
    adapter: str,
    signal_count: int,
    error: Optional[str],
) -> None:
    conn.execute(
        """
        INSERT INTO sb_sync_state (adapter, last_run_at, signal_count, error)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(adapter) DO UPDATE SET
          last_run_at  = excluded.last_run_at,
          signal_count = excluded.signal_count,
          error        = excluded.error
        """,
        (adapter, _now_utc(), signal_count, error),
    )
    conn.commit()


def _record_state_fresh(
    db_path: Path | str,
    *,
    adapter: str,
    signal_count: int,
    error: Optional[str],
) -> None:
    """Open a fresh connection to record state (used after subprocess termination)."""
    from ..store.db import connect

    conn = connect(db_path)
    try:
        _record_state(conn, adapter=adapter, signal_count=signal_count, error=error)
    finally:
        conn.close()


def get_sync_states(conn: sqlite3.Connection) -> list[dict]:
    """Return all rows from ``sb_sync_state`` as plain dicts."""
    rows = conn.execute(
        "SELECT adapter, last_run_at, signal_count, error"
        " FROM sb_sync_state ORDER BY adapter"
    ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Thread-based runner (bounded timeout via t.join + daemon thread)
# ---------------------------------------------------------------------------


def run_adapter(
    name: str,
    fn: Callable[[sqlite3.Connection], int],
    db_path: Path | str,
    *,
    timeout: float = 30.0,
) -> AdapterResult:
    """Run *fn* in a daemon thread that opens its own SQLite connection.

    *No* connection crosses thread boundaries.  The call returns within
    ``timeout + small_epsilon`` seconds even if the fn is still running —
    the daemon thread will be cleaned up when the process exits.
    """
    from ..store.db import connect

    result_holder: list[int] = []
    error_holder: list[str] = []

    def worker() -> None:
        conn = connect(db_path)
        try:
            count = fn(conn)
            _record_state(conn, adapter=name, signal_count=count, error=None)
            result_holder.append(count)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc) or repr(exc)
            try:
                _record_state(conn, adapter=name, signal_count=0, error=msg)
            except Exception:  # noqa: BLE001
                pass
            error_holder.append(msg)
        finally:
            conn.close()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        # Thread is stuck; return immediately (daemon thread dies with process)
        msg = f"adapter {name!r} timed out after {timeout}s"
        logger.warning(msg)
        # Record state from the calling thread with a fresh connection
        try:
            _record_state_fresh(db_path, adapter=name, signal_count=0, error=msg)
        except Exception:  # noqa: BLE001
            pass
        return AdapterResult(adapter=name, error=msg)

    if error_holder:
        msg = error_holder[0]
        logger.warning("adapter %r failed: %s", name, msg)
        return AdapterResult(adapter=name, error=msg)

    if result_holder:
        return AdapterResult(adapter=name, signal_count=result_holder[0])

    return AdapterResult(adapter=name, error="adapter produced no result")


# ---------------------------------------------------------------------------
# Subprocess-based runner (production, truly bounded timeout via p.terminate)
# ---------------------------------------------------------------------------


def _dispatch_by_name(name: str, conn: sqlite3.Connection, config: dict) -> int:
    """Dispatch to the named adapter function.  Runs inside a subprocess worker."""
    roots = [Path(r) for r in config.get("roots", [])]
    since_days = int(config.get("since_days", 30))
    git_authors: Optional[list[str]] = config.get("git_authors") or None

    if name == "todos":
        from sb_core.adapters.todos import run  # type: ignore[import]

        return run(conn)
    if name == "jira":
        from sb_core.adapters.jira import run  # type: ignore[import]

        return run(conn)
    if name == "changelog":
        from sb_core.adapters.changelog import run  # type: ignore[import]

        return run(conn, roots=roots)
    if name == "git":
        from sb_core.adapters.git import run  # type: ignore[import]

        return run(conn, roots=roots, since_days=since_days, authors=git_authors)
    if name == "webex":
        from sb_core.adapters.webex import run  # type: ignore[import]

        return run(conn)
    raise ValueError(f"unknown adapter: {name!r}")


def _subprocess_worker(
    name: str,
    db_path: str,
    config: dict,
    result_queue,  # multiprocessing.Queue
) -> None:
    """Top-level subprocess entry point (must be a module-level function for spawn).

    Opens its own SQLite connection — no connection crosses process boundaries.
    """
    from sb_core.store.db import connect  # type: ignore[import]

    conn = connect(db_path)
    try:
        count = _dispatch_by_name(name, conn, config)
        _record_state(conn, adapter=name, signal_count=count, error=None)
        result_queue.put(("ok", count))
    except Exception as exc:  # noqa: BLE001
        msg = str(exc) or repr(exc)
        try:
            _record_state(conn, adapter=name, signal_count=0, error=msg)
        except Exception:  # noqa: BLE001
            pass
        result_queue.put(("error", msg))
    finally:
        conn.close()


def run_adapter_by_name(
    name: str,
    db_path: Path | str,
    config: dict,
    *,
    timeout: float = 30.0,
) -> AdapterResult:
    """Subprocess-based adapter runner with a truly bounded timeout.

    The worker process opens its own SQLite connection, dispatches by name,
    and is ``terminate()``-ed if it runs past ``timeout`` seconds.

    Works on macOS with the default ``spawn`` start method.
    """
    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(
        target=_subprocess_worker,
        kwargs={
            "name": name,
            "db_path": str(db_path),
            "config": config,
            "result_queue": q,
        },
    )
    p.start()
    p.join(timeout=timeout)

    if p.is_alive():
        p.terminate()
        p.join(timeout=5.0)
        if p.is_alive():
            p.kill()
            p.join()
        msg = f"adapter {name!r} timed out after {timeout}s"
        logger.warning(msg)
        # Worker was killed before it could record state; do it from main process
        try:
            _record_state_fresh(db_path, adapter=name, signal_count=0, error=msg)
        except Exception:  # noqa: BLE001
            pass
        return AdapterResult(adapter=name, error=msg)

    # Process exited; check result queue
    if not q.empty():
        try:
            kind, value = q.get_nowait()
            if kind == "ok":
                return AdapterResult(adapter=name, signal_count=int(value))
            return AdapterResult(adapter=name, error=str(value))
        except Exception:  # noqa: BLE001
            pass

    if p.exitcode != 0:
        msg = f"adapter {name!r} exited with code {p.exitcode}"
        try:
            _record_state_fresh(db_path, adapter=name, signal_count=0, error=msg)
        except Exception:  # noqa: BLE001
            pass
        return AdapterResult(adapter=name, error=msg)

    return AdapterResult(adapter=name, error=f"adapter {name!r} produced no result")
