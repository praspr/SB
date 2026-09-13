"""Entry point: builds FastMCP + FastAPI, mounts them together, runs uvicorn.

Both MCP tools and REST endpoints are backed by the same handler functions
in handlers.py, so behaviour cannot drift between transports.

MCP is mounted at /mcp using FastMCP's streamable-http transport. The
FastMCP ASGI app's lifespan is passed through to FastAPI (required for the
MCP session manager to initialize) using combine_lifespans.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.utilities.lifespan import combine_lifespans

from . import __version__
from .config import settings
from .db import get_conn
from .mcp_tools import mcp
from .rest_routes import router as todos_router

# FastMCP's ASGI app, mounted at "/mcp". path="/" avoids a double "/mcp/mcp" prefix.
mcp_app = mcp.http_app(path="/", transport="http")


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Ensure the DB connection + migrations are initialized on startup.
    get_conn()
    yield


app = FastAPI(
    title="sb-todos",
    version=__version__,
    lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(todos_router)
app.mount("/mcp", mcp_app)


@app.get("/health")
def health() -> dict:
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
    return {"status": "ok", "version": __version__, "todos_count": count}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "sb_todos.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
