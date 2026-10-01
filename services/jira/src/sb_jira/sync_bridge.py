"""Best-effort soft bridge from sb-jira sync to the sb-core sync lock +
ledger logging (phase 2j).

sb-jira may run standalone (no sb-core installed) so every reference to
``sb_core`` here is deliberately deferred and wrapped. In production,
sb-jira's MCP tools are mounted directly inside the sb-core process (see
``services/core/src/sb_core/mcp_app.py``), so ``sb_core`` is genuinely
importable there and the real advisory lock + ledger write apply. When run
standalone (this package's own test suite, or a future standalone
deployment), there is no cross-process scheduler to race against, so the
lock degrades to "always acquired" and the ledger write is simply skipped.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


@contextmanager
def sync_lock(adapter: str) -> Iterator[bool]:
    """Soft-imports ``sb_core.sync_logger.sync_lock``. Degrades to an
    always-acquired no-op lock when sb-core is not installed."""
    try:
        from sb_core.sync_logger import sync_lock as _core_sync_lock
    except Exception as exc:  # noqa: BLE001
        logger.warning("sync_bridge.sync_lock: sb_core unavailable, no-op lock: %s", exc)
        yield True
        return

    with _core_sync_lock(adapter) as acquired:
        yield acquired


def record_sync(
    adapter: str, counts: dict[str, Any], errors: Optional[list[str]] = None
) -> None:
    """Soft-imports ``sb_core.sync_logger.record_sync``. Swallows all
    errors, including sb_core being unavailable."""
    try:
        from sb_core.sync_logger import record_sync as _core_record_sync
    except Exception as exc:  # noqa: BLE001
        logger.warning("sync_bridge.record_sync: sb_core unavailable: %s", exc)
        return
    try:
        _core_record_sync(adapter, counts, errors)
    except Exception as exc:  # noqa: BLE001
        logger.warning("sync_bridge.record_sync failed for %s: %s", adapter, exc)
