"""FastMCP tool registrations for the pull-only sb-jira library."""

from __future__ import annotations

import re

from fastmcp import FastMCP

from . import atlassian_client, file_store, format, history, sync, tracking
from .config import settings

mcp = FastMCP(
    name="sb-jira",
    instructions=(
        "Read-only JIRA browser. Reads local markdown mirror at "
        "ciq/docs/jira/tickets/*.md. Refresh pulls from Atlassian → files only; "
        "never writes to Atlassian."
    ),
)


@mcp.tool()
def list_jira_tickets(
    status: str | None = None,
    priority: str | None = None,
    project: str | None = None,
    projects: list[str] | None = None,
    q: str | None = None,
    hide_closed: bool = False,
    limit: int = 100,
) -> list[dict]:
    """List JIRA tickets from the local markdown mirror. Read-only.

    Args:
        status: Exact status match, e.g. 'Open', 'In Engineering Review', 'Closed'.
        priority: Exact priority match, e.g. 'Highest', 'High', 'Medium', 'Low', 'Lowest'.
        project: Exact project key match, e.g. 'CXP', 'CXPL'.
        projects: Match any of these project keys. Used by the multi-select filter.
        q: Case-insensitive substring match against "{key} {title}".
        hide_closed: Omit Closed, Done, Resolved, and Cancelled unless a status is set.
        limit: Maximum number of tickets to return (default 100).
    """
    details = file_store.load_all()
    tickets = [file_store.to_ticket(d) for d in details]
    filtered = file_store.apply_filters(
        tickets,
        status=status,
        priority=priority,
        project=project,
        projects=projects,
        q=q,
        hide_closed=hide_closed,
    )
    tracked = set(tracking.load_keys())
    return [
        {**ticket.model_dump(mode="json"), "tracked": ticket.key in tracked}
        for ticket in filtered[:limit]
    ]


@mcp.tool()
def get_jira_ticket(key: str) -> dict | None:
    """Get one JIRA ticket by key (e.g. 'CXP-45827'). Returns full detail with sections.

    Returns None if the ticket does not exist in the local mirror.
    """
    detail = file_store.load_by_key(key)
    return detail.model_dump(mode="json") if detail else None


@mcp.tool()
def track_jira(issue: str) -> dict:
    """Fetch one JIRA by key or browse URL and keep it in the local mirror.

    The fetch is read-only. The key stays tracked until untrack_jira removes it.
    """
    try:
        key = tracking.parse_issue(issue, settings.atlassian_site)
    except ValueError as exc:
        return {"key": None, "tracked": False, "errors": [str(exc)]}
    try:
        ticket = atlassian_client.fetch_issue(key)
    except atlassian_client.AtlassianAuthError as exc:
        return {"key": key, "tracked": False, "errors": [str(exc)]}
    except atlassian_client.AtlassianClientError as exc:
        return {"key": key, "tracked": False, "errors": [str(exc)]}
    ticket.file_path = format.file_path_for(key)
    sync._write_ticket_file(ticket, settings.tickets_dir)
    tracking.add_key(key)
    tickets = file_store.load_all()
    history.regenerate_readme(tickets)
    return {"key": key, "tracked": True, "errors": []}


@mcp.tool()
def untrack_jira(key: str) -> dict:
    """Stop refreshing a tracked JIRA. The local markdown file is kept."""
    try:
        parsed = tracking.parse_issue(key, settings.atlassian_site)
    except ValueError as exc:
        return {"key": None, "tracked": False, "errors": [str(exc)]}
    tracking.remove_key(parsed)
    return {"key": parsed, "tracked": False, "errors": []}


@mcp.tool()
def sync_jira() -> dict:
    """Pull latest tickets from Atlassian and rewrite the local markdown mirror.

    Never writes to Atlassian — this is a one-directional, read-only pull.
    Returns update/added/unchanged counts plus any errors encountered.
    """
    return sync.run_sync().model_dump(mode="json")


def _last_sync_at() -> str | None:
    """Read the latest local SYNC date. Does not contact Atlassian."""
    path = settings.tickethistory_path
    try:
        if not path.is_file() or path.is_symlink():
            return None
        if path.stat().st_size > 1_000_000:
            return None
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    # tickethistory.md is newest-first. A legacy row uses "SYNC" in column 2;
    # the maintained history uses the activity date in column 1.
    for line in text.splitlines():
        cells = [cell.strip().strip("*") for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            return cells[0]
    return None


@mcp.tool()
def jira_status() -> dict:
    """Return local ticket count, last sync, and Atlassian reachability.

    Reachability is a read-only probe. This tool never writes to Atlassian.
    """
    reachable, error = atlassian_client.probe_reachable()
    tickets = file_store.load_all()
    return {
        "atlassian_reachable": reachable,
        "atlassian_error": error,
        "tickets_count": len(tickets),
        "tracked_count": len(tracking.load_keys()),
        "last_sync_at": _last_sync_at(),
    }
