"""ASGI host for the unified sb MCP transports and health route."""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, HTTPException

from . import __version__
from .config import settings
from .mcp_app import mcp, system_status
from .store.db import connect

mcp_http_app = mcp.http_app(path="/mcp", transport="http")
mcp_sse_app = mcp.http_app(path="/sse", transport="sse")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    conn = connect(settings.db_path)
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
