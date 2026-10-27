"""Access gate for write-capable MCP tools (M5).

A FastMCP middleware that intercepts ``tools/call`` and, for the
write-capable subset, requires a valid local token (see ``local_token.py``).
Read tools are never gated, preserving localhost ergonomics.

Staged rollout, controlled by env (read via ``config.settings``):
- ``SB_CORE_REQUIRE_LOCAL_TOKEN`` unset/false (default): **observe-only**.
  Missing/invalid tokens are logged once per tool name but the call proceeds.
- ``SB_CORE_REQUIRE_LOCAL_TOKEN`` true: **enforce**. Write tools without a
  valid token are rejected before execution.

The token is read from the ``X-SB-Local-Token`` HTTP header when the call
arrives over HTTP. The token value itself is never logged.
"""

from __future__ import annotations

import logging

from fastmcp.server.middleware import Middleware, MiddlewareContext

from . import local_token

logger = logging.getLogger(__name__)

_HEADER_NAME = "x-sb-local-token"

# Write-capable tools across all submounts. Mounted names are unprefixed
# (FastMCP mounts preserve original tool names in this codebase).
WRITE_TOOLS: frozenset[str] = frozenset(
    {
        # todos (write)
        "todo_add",
        "todo_update",
        "todo_complete",
        "todo_uncomplete",
        "todo_delete",
        "expand_recurring_todo",
        # ledger (append)
        "ledger_log",
        "ledger_batch_log",
        "ledger_register_project",
        "sync_ledger_from_files",
        # webex (the one write tool)
        "webex_post_message",
        # goals (write)
        "add_goal",
        "update_goal",
        "archive_goal",
        # scheduler (write)
        "add_scheduled_ritual",
        "delete_scheduled_ritual",
        # proposals / rituals that persist
        "approve_proposal",
        "reject_proposal",
        # jira local-mirror mutations
        "track_jira",
        "untrack_jira",
        "bulk_import_jira_to_todos",
        # webex local handled/mute state
        "webex_mark_handled",
        "webex_mark_unhandled",
        "mute_space",
        "unmute_space",
    }
)


class LocalTokenError(RuntimeError):
    """Raised when a write-capable tool is called without a valid local token."""


def _require_enabled() -> bool:
    from .config import settings

    return bool(getattr(settings, "require_local_token", False))


def _extract_token() -> str | None:
    """Read the local token from the current HTTP request headers, if any."""
    try:
        from fastmcp.server.dependencies import get_http_headers

        headers = get_http_headers() or {}
    except Exception:
        return None
    # Header lookups are case-insensitive in the mapping FastMCP returns, but
    # normalize defensively.
    for key, value in headers.items():
        if key.lower() == _HEADER_NAME:
            return value
    return None


# Track which tools we've already warned about in observe mode, to avoid log spam.
_observed_warned: set[str] = set()


class WriteToolGate(Middleware):
    """Gate write-capable tools behind the local token."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = getattr(context.message, "name", None)
        if tool_name in WRITE_TOOLS:
            candidate = _extract_token()
            ok = local_token.token_matches(candidate)
            if not ok:
                if _require_enabled():
                    raise LocalTokenError(
                        f"tool {tool_name!r} requires a valid local token "
                        "(X-SB-Local-Token). See docs: M5 access gate."
                    )
                if tool_name not in _observed_warned:
                    _observed_warned.add(tool_name)
                    logger.warning(
                        "[local-gate] observe-only: %r called without a valid "
                        "local token (enforcement off)",
                        tool_name,
                    )
        return await call_next(context)
