"""ASGI host for the unified sb MCP transports and health route."""

from __future__ import annotations

import asyncio
import html
import logging
import mimetypes
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from . import __version__
from .config import settings
from .cursor_auth import get_cursor_cookie
from .mcp_app import mcp, system_status
from .skills import refresh_skill_surface
from .store.db import connect

mcp_http_app = mcp.http_app(path="/mcp", transport="http")
mcp_sse_app = mcp.http_app(path="/sse", transport="sse")
logger = logging.getLogger("sb_core.scheduler")

_CURSOR_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128 Safari/537.36"
)
_DASHBOARD_NOT_BUILT_HTML = (
    "<!doctype html><html><body><h1>503 — dashboard not built</h1>"
    "<p>Run <code>npm run build</code> in sb/web, then restart sb-core.</p>"
    "</body></html>"
)


async def _scheduler_loop() -> None:
    """Evaluate local schedules in the existing sb-core process."""
    from .scheduler import run_due_schedules

    while True:
        await asyncio.sleep(300)
        try:
            await asyncio.to_thread(run_due_schedules)
        except Exception:
            logger.exception("scheduled runner failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    conn = connect(settings.db_path)
    try:
        refresh_skill_surface(mcp, conn)
    finally:
        conn.close()
    scheduler_task = asyncio.create_task(_scheduler_loop())
    try:
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(mcp_http_app.lifespan(mcp_http_app))
            await stack.enter_async_context(mcp_sse_app.lifespan(mcp_sse_app))
            yield
    finally:
        scheduler_task.cancel()
        await asyncio.gather(scheduler_task, return_exceptions=True)


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


@app.get("/proxy/claudegate/{rest_of_path:path}")
async def proxy_claudegate(rest_of_path: str, request: Request) -> Response:
    """Forward requests to the local claudegate LLM gateway (localhost:9999)."""
    url = f"http://localhost:9999/{rest_of_path}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            upstream = await client.get(url, params=request.query_params)
    except httpx.HTTPError as exc:
        logger.warning("claudegate proxy failed: %s", exc)
        return Response(
            content='{"error": "claudegate upstream unavailable"}',
            status_code=502,
            media_type="application/json",
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


@app.get("/proxy/cursor/{rest_of_path:path}")
async def proxy_cursor(rest_of_path: str, request: Request) -> Response:
    """Forward requests to cursor.com with the local desktop session cookie."""
    url = f"https://cursor.com/{rest_of_path}"
    headers = {"Accept": "application/json", "User-Agent": _CURSOR_USER_AGENT}
    cookie = get_cursor_cookie()
    if cookie:
        headers["Cookie"] = cookie
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            upstream = await client.get(
                url, params=request.query_params, headers=headers
            )
    except httpx.HTTPError as exc:
        logger.warning("cursor proxy failed: %s", exc)
        return Response(
            content='{"error": "cursor upstream unavailable"}',
            status_code=502,
            media_type="application/json",
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


def _web_dist_dir() -> Path:
    return settings.web_dist_path


def _serve_spa_file(rel_path: str) -> Response:
    """Serve a file from the built SPA directory, falling back to index.html.

    Returns a 503 placeholder if the dist directory or index.html is missing.
    """
    dist_dir = _web_dist_dir()
    index_path = dist_dir / "index.html"
    if not index_path.is_file():
        return HTMLResponse(_DASHBOARD_NOT_BUILT_HTML, status_code=503)

    candidate = (dist_dir / rel_path).resolve()
    try:
        candidate.relative_to(dist_dir.resolve())
    except ValueError:
        candidate = index_path  # path traversal attempt — fall back safely

    target = candidate if candidate.is_file() else index_path
    media_type, _ = mimetypes.guess_type(str(target))
    return Response(content=target.read_bytes(), media_type=media_type or "application/octet-stream")


@app.get("/_ui")
async def ui_root() -> RedirectResponse:
    return RedirectResponse(url="/_ui/")


@app.get("/_ui/")
async def ui_index() -> Response:
    return _serve_spa_file("index.html")


@app.get("/_ui/{rest_of_path:path}")
async def ui_catch_all(rest_of_path: str) -> Response:
    return _serve_spa_file(rest_of_path)


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
