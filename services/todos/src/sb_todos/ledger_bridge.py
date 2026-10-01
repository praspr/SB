"""Best-effort soft bridge from todo CRUD mutations to the sb-core ledger.

The todos service may run standalone (no sb-core installed) so every import
of ``sb_core`` here is deliberately deferred and wrapped: if sb-core is not
importable, or the ledger write errors for any reason, the todo mutation
itself must still succeed. We only log a warning and move on.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def record(
    action_verb: str,
    summary: str,
    body: str | None,
    refs: list[dict] | None,
) -> None:
    """Best-effort ledger write. Swallows all errors.

    Uses ``sb_core.ledger_tools.ledger_log`` (not the raw storage primitive)
    so that session resolution and CHANGELOG.md dual-sync happen exactly as
    they would for any other MCP-originated ledger entry.
    """
    try:
        from sb_core.ledger_tools import ledger_log

        ledger_log(
            summary=summary,
            project="sb",
            action_verb=action_verb,
            body=body,
            refs=refs or [],
            agent="todos-service",
            working_dir=os.getcwd(),
            source_harness="todos-mcp",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ledger bridge failed: %s", exc)
