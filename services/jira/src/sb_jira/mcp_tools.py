"""FastMCP tool registrations for the pull-only sb-jira library."""

from __future__ import annotations

from fastmcp import FastMCP

from . import atlassian_client, file_store, sync
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
    q: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """List JIRA tickets from the local markdown mirror. Read-only.

    Args:
        status: Exact status match, e.g. 'Open', 'In Engineering Review', 'Closed'.
        priority: Exact priority match, e.g. 'Highest', 'High', 'Medium', 'Low', 'Lowest'.
        project: Exact project key match, e.g. 'CXP', 'CXPL'.
        q: Case-insensitive substring match against "{key} {title}".
        limit: Maximum number of tickets to return (default 100).
    """
    details = file_store.load_all()
    tickets = [file_store.to_ticket(d) for d in details]
    filtered = file_store.apply_filters(
        tickets, status=status, priority=priority, project=project, q=q
    )
    return [t.model_dump(mode="json") for t in filtered[:limit]]


@mcp.tool()
def get_jira_ticket(key: str) -> dict | None:
    """Get one JIRA ticket by key (e.g. 'CXP-45827'). Returns full detail with sections.

    Returns None if the ticket does not exist in the local mirror.
    """
    detail = file_store.load_by_key(key)
    return detail.model_dump(mode="json") if detail else None


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
    last: str | None = None
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[1] == "SYNC" and cells[0]:
            last = cells[0]
    return last


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
        "last_sync_at": _last_sync_at(),
    }
