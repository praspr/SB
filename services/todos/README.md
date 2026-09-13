# sb-todos

A local todos service backed by SQLite, exposed **both** as MCP tools (for
Cursor / OpenCode / Claude Code) and as REST endpoints (for the `sb` web
app). Both transports call the same pure handler functions in
`handlers.py`, so behaviour cannot drift between them.

## Storage

SQLite database at `~/.local/share/sb/todos.db` (parent directories are
created automatically on first run). WAL journal mode, `busy_timeout=5000`,
foreign keys on.

Override via environment variables (prefix `SB_TODOS_`):

- `SB_TODOS_DB_PATH` — path to the SQLite file
- `SB_TODOS_HOST` — bind host (default `127.0.0.1`)
- `SB_TODOS_PORT` — bind port (default `8788`)
- `SB_TODOS_CORS_ORIGIN` — allowed browser origin (default `http://localhost:5173`)

## Running

```bash
cd sb/services/todos
uv sync
uv run uvicorn sb_todos.main:app --host 127.0.0.1 --port 8788
```

Or via launchd — see `launchd/com.praspr.sb-todos.plist`. Install with:

```bash
cp launchd/com.praspr.sb-todos.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.praspr.sb-todos.plist
```

## Dual transport

Both MCP and REST are served from the **same process and the same port**
(`127.0.0.1:8788`), via FastMCP's ASGI mounting support:

- FastMCP builds its tool server (`FastMCP("sb-todos")` in `mcp_tools.py`)
  and exposes it as a Starlette ASGI app via `mcp.http_app(path="/",
  transport="http")` (streamable-HTTP transport, the modern successor to
  plain SSE in FastMCP 2.x/3.x/4.x).
- That ASGI app is mounted onto the main FastAPI app at `/mcp` in
  `main.py`.
- The FastMCP app's `lifespan` is combined with the FastAPI app's own
  startup logic via `fastmcp.utilities.lifespan.combine_lifespans` — this
  is required for FastMCP's session manager to initialize; without it,
  requests to `/mcp` would fail.
- REST routes are registered as an ordinary `APIRouter` (`rest_routes.py`)
  and included directly on the FastAPI app.

No fallback to a second port was needed — the installed FastMCP version
(4.x) supports clean single-port ASGI mounting.

### MCP client endpoint

- Streamable HTTP: `http://127.0.0.1:8788/mcp/`

Point your MCP client (Cursor, OpenCode, Claude Code, etc.) at that URL
using the streamable-HTTP transport. A plain unauthenticated `GET` to that
URL will return `400 Bad Request` — that's expected, it means the endpoint
is live but requires a proper MCP session handshake (initialize request
with the correct headers), not a browser-style GET.

### REST endpoints

All under `http://127.0.0.1:8788/api/todos`:

| Method + Path | Description |
|---|---|
| `GET /api/todos` | List todos. Query params: `status` (open\|completed\|all, default open), `priority`, `domain`, `tag`, `limit` |
| `GET /api/todos/search?q=...&limit=...` | Search todos by title/description substring |
| `GET /api/todos/{id}` | Fetch a single todo |
| `POST /api/todos` | Create a todo (body: `TodoCreate`) |
| `PATCH /api/todos/{id}` | Update a todo (body: `TodoUpdate`, partial) |
| `POST /api/todos/{id}/complete` | Mark completed |
| `POST /api/todos/{id}/uncomplete` | Mark not completed |
| `DELETE /api/todos/{id}` | Delete a todo |

Plus `GET /health` → `{"status": "ok", "version": "0.1.0", "todos_count": N}`.

CORS is enabled for `http://localhost:5173` (the sb web app's dev origin),
configurable via `SB_TODOS_CORS_ORIGIN`.

### MCP tools

Same surface, exposed as MCP tools with snake_case names:

`todo_list`, `todo_get`, `todo_add`, `todo_complete`, `todo_uncomplete`,
`todo_update`, `todo_delete`, `todo_search`.

## Idempotent external upsert

`todo_add` / `POST /api/todos` accept optional `external_source` +
`external_ref` (e.g. `"jira"` / `"CXP-45827"`). If a todo with that pair
already exists, it's updated in place rather than duplicated — this is
enforced both by application logic in `handlers.add_todo` and by a unique
partial index (`idx_todos_ext`) in the schema.

## Tests

```bash
cd sb/services/todos
uv sync --extra dev
uv run pytest tests/ -q
```

- `test_db.py` — migration runner: creates tables, is idempotent, columns match schema.
- `test_handlers.py` — full CRUD round-trip against an in-memory SQLite DB, search, external-ref upsert.
- `test_rest.py` — FastAPI `TestClient` covering all REST endpoints + `/health`.
- `test_mcp.py` — imports `mcp_tools` and asserts all 8 tools are registered with docstrings.

## Project layout

```
sb/services/todos/
├── pyproject.toml
├── README.md
├── src/sb_todos/
│   ├── __init__.py
│   ├── main.py            # entry: wires FastMCP + FastAPI together, uvicorn app
│   ├── config.py          # env-overridable settings
│   ├── models.py          # Pydantic models
│   ├── db.py               # sqlite3 connection singleton + migration runner
│   ├── migrations/001_init.sql
│   ├── handlers.py         # pure functions shared by both transports
│   ├── mcp_tools.py        # @mcp.tool wrappers
│   └── rest_routes.py      # FastAPI router
├── tests/
├── launchd/com.praspr.sb-todos.plist
```
