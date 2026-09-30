"""ASGI host for the unified sb MCP transports and health route."""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager

import html

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from . import __version__
from .config import settings
from .mcp_app import mcp, system_status
from .skills import refresh_skill_surface
from .store.db import connect

mcp_http_app = mcp.http_app(path="/mcp", transport="http")
mcp_sse_app = mcp.http_app(path="/sse", transport="sse")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    conn = connect(settings.db_path)
    try:
        refresh_skill_surface(mcp, conn)
    finally:
        conn.close()
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_http_app.lifespan(mcp_http_app))
        await stack.enter_async_context(mcp_sse_app.lifespan(mcp_sse_app))
        yield


app = FastAPI(
    title="sb-core",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return await system_status()


@app.get("/webex/login")
def webex_login() -> RedirectResponse:
    """Start Webex OAuth. Tokens are stored in the keychain, not in this redirect."""
    from sb_webex.client import begin_login

    redirect = f"http://{settings.host}:{settings.port}/webex/callback"
    return RedirectResponse(begin_login(redirect))


@app.get("/webex/callback")
def webex_callback(code: str = "", state: str = "") -> HTMLResponse:
    """Finish Webex OAuth. The authorization code is not written to the page."""
    from sb_webex.client import WebexAuthError, finish_login

    try:
        finish_login(code, state)
    except WebexAuthError as exc:
        return HTMLResponse(
            f"<p>{html.escape(str(exc))}</p>",
            status_code=400,
        )
    return HTMLResponse("<p>Webex is signed in. Return to the dashboard and sync.</p>")


@app.api_route(
    "/api",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
@app.api_route(
    "/api/{rest_of_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def retired_rest(_rest_of_path: str = "") -> None:
    """Domain traffic is MCP-only. Retired REST prefixes stay absent."""
    raise HTTPException(status_code=404, detail="Not Found")


# FastMCP owns these transport routes. Extending the host router keeps the
# configured endpoints exact (/mcp and /sse) without redirecting POSTs.
app.router.routes.extend(mcp_http_app.routes)
app.router.routes.extend(mcp_sse_app.routes)
