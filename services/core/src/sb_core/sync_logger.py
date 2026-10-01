"""Advisory file lock + best-effort ledger logging for sync operations.

Design (phase 2j):
- ``sync_lock`` is a per-adapter advisory lock using ``fcntl.flock`` on a
  lock file under ``~/.local/share/sb/sync-locks/``. Concurrent fires of the
  same adapter's sync must return ``{"status": "already_running"}`` without
  doing work and without logging (see callers in webex_tools/sync_tools/
  ledger_tools/scheduler).
- ``record_sync`` writes one best-effort ``Synced`` ledger row per
  completed sync run, using ``ledger_tools.ledger_log`` (not the raw
  ``append_ledger`` storage primitive) so CHANGELOG.md dual-sync and
  session resolution happen the same way any other ledger entry does.
- The ledger's own ``content_sha256`` idempotency only dedupes on
  project+summary+body, which do not naturally vary run-to-run for a
  "(no changes)" sync. We fold the current UTC minute into the body so a
  repeat sync in the same second still dedupes, while a genuinely later
  sync (next minute) gets its own row -- this is what makes the
  scheduler-alive signal visible in the ledger.
"""

from __future__ import annotations

import fcntl
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)
LOCK_DIR = Path("~/.local/share/sb/sync-locks").expanduser()


@contextmanager
def sync_lock(adapter: str) -> Iterator[bool]:
    """Yields True when the lock is acquired exclusively, False when another
    sync is already running. On False, caller should return
    ``{"status": "already_running"}`` without doing work and without logging.
    """
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    path = LOCK_DIR / f"{adapter}.lock"
    with open(path, "w") as fp:
        try:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError:
            acquired = False
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
                except Exception:  # noqa: BLE001
                    pass


def record_sync(
    adapter: str,
    counts: dict[str, Any],
    errors: Optional[list[str]] = None,
    *,
    now: Optional[datetime] = None,
) -> None:
    """Best-effort ledger write for a completed sync run.

    Uses the current UTC minute (or the injected ``now`` for testability)
    in the ledger body so duplicate same-minute runs dedupe via
    ``content_sha256`` but one row per minute is preserved. Swallows all
    errors to keep sync paths robust -- a ledger write failure must never
    fail the sync itself.
    """
    try:
        from .ledger_tools import ledger_log

        moment = now or datetime.now(timezone.utc)
        minute = moment.strftime("%Y-%m-%dT%H:%MZ")

        # terse "no changes" summary when every numeric count is zero
        numeric = {k: v for k, v in counts.items() if isinstance(v, int)}
        changed = any(v > 0 for v in numeric.values())
        if changed:
            summary = f"Synced {adapter}: " + ", ".join(
                f"{k}={v}" for k, v in numeric.items()
            )
        else:
            summary = f"Synced {adapter} (no changes)"

        body_lines = [f"adapter: {adapter}", f"minute: {minute}"]
        body_lines.extend(f"{k}: {v}" for k, v in counts.items())
        if errors:
            body_lines.append("errors: " + "; ".join(str(e) for e in errors))
        body = "\n".join(body_lines)

        ledger_log(
            summary=summary,
            project="sb",
            action_verb="Synced",
            body=body,
            refs=[{"kind": "sync", "value": adapter}],
            agent="sync-adapter",
            working_dir=os.getcwd(),
            source_harness="scheduler",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("sync_logger.record_sync failed for %s: %s", adapter, exc)
