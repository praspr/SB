"""FastAPI app + uvicorn entry point for sb-jira."""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import atlassian_client, file_store, sync
from .config import settings
from .mcp_tools import mcp
from .models import HealthResponse, JiraTicket, JiraTicketDetail, RefreshResult, StatusResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sb_jira.main")

_state: dict[str, str | None] = {"last_sync_at": None}

# MCP is served on the same port, mounted under /mcp. FastMCP 4.x defaults its
# internal streamable-HTTP route to "/mcp", so we mount it at path="/" and
# let the FastAPI `app.mount("/mcp", ...)` prefix provide the "/mcp" segment.
# An SSE transport is also exposed at /mcp/sse for clients that expect it.
mcp_http_app = mcp.http_app(path="/", transport="http")
mcp_sse_app = mcp.http_app(path="/", transport="sse")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("sb-jira starting up")
    logger.info("tickets_dir=%s", settings.tickets_dir)
    logger.info("readme_path=%s", settings.readme_path)
    logger.info("tickethistory_path=%s", settings.tickethistory_path)
    reachable, error = atlassian_client.probe_reachable()
    if reachable:
        logger.info("Atlassian reachable")
    else:
        logger.warning("Atlassian not reachable: %s", error)

    # Combine our own startup logic with the mounted FastMCP sub-apps'
    # lifespans, so their session managers actually get started/stopped.
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_http_app.lifespan(mcp_http_app))
        await stack.enter_async_context(mcp_sse_app.lifespan(mcp_sse_app))
        yield


app = FastAPI(title="sb-jira", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_app_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/mcp/sse", mcp_sse_app)


@app.get("/mcp/sse", include_in_schema=False)
async def _mcp_sse_no_trailing_slash_redirect() -> RedirectResponse:
    """Starlette's Mount matching requires a trailing slash; alias the bare
    '/mcp/sse' path (no trailing slash) to the mounted SSE app so both forms
    are reachable rather than 404ing."""
    return RedirectResponse(url="/mcp/sse/")


app.mount("/mcp", mcp_http_app)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    tickets = file_store.load_all()
    return HealthResponse(status="ok", version="0.1.0", tickets_on_disk=len(tickets))


@app.get("/api/jira/tickets", response_model=list[JiraTicket])
async def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    project: str | None = None,
    q: str | None = None,
) -> list[JiraTicket]:
    details = file_store.load_all()
    tickets = [file_store.to_ticket(d) for d in details]
    return file_store.apply_filters(tickets, status=status, priority=priority, project=project, q=q)


@app.get("/api/jira/tickets/{key}", response_model=JiraTicketDetail)
async def get_ticket(key: str) -> JiraTicketDetail:
    path = settings.tickets_dir / f"{key}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Ticket {key} not found")
    try:
        return file_store.load(path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Failed to parse ticket {key}: {exc}") from exc


@app.post("/api/jira/sync", response_model=RefreshResult)
async def sync_tickets() -> RefreshResult:
    result = sync.run_sync()
    if not result.errors:
        _state["last_sync_at"] = datetime.now(timezone.utc).isoformat()
    return result


@app.get("/api/jira/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    tickets = file_store.load_all()
    reachable, error = atlassian_client.probe_reachable()
    return StatusResponse(
        last_sync_at=_state["last_sync_at"],
        atlassian_reachable=reachable,
        atlassian_error=error,
        tickets_count=len(tickets),
    )


def run() -> None:
    import uvicorn

    uvicorn.run("sb_jira.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()
