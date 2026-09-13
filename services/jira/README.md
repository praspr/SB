# sb-jira

Read-only Python HTTP service that serves local JIRA ticket mirrors
(`ciq/docs/jira/tickets/*.md`) to the `sb` web app, plus a one-directional
"Refresh from Atlassian" sync (Atlassian → files only).

**This service never writes to Atlassian.**

## Run

```bash
cd sb/services/jira
uv sync
uv run uvicorn sb_jira.main:app --host 127.0.0.1 --port 8789
```

## Endpoints

| Method + Path | Purpose |
|---|---|
| `GET /health` | Liveness + ticket count on disk |
| `GET /api/jira/tickets` | List all tickets from local files |
| `GET /api/jira/tickets/{key}` | Single ticket with full body/sections |
| `POST /api/jira/sync` | Pull from Atlassian, rewrite local files (read-only against Atlassian) |
| `GET /api/jira/status` | Sync state + Atlassian reachability |

## Config

All paths/settings are overridable via `SB_JIRA_*` environment variables
(see `src/sb_jira/config.py`), e.g. `SB_JIRA_TICKETS_DIR`, `SB_JIRA_PORT`.

Atlassian API token is read from macOS Keychain via `keyring`
(`service="sb"`, `username="jira.token"`), falling back to the
`ATLASSIAN_API_TOKEN` environment variable. If no token is configured,
`/api/jira/sync` returns HTTP 200 with an `errors` entry rather than failing.

## MCP

Alongside the REST endpoints, `sb-jira` exposes the same read-only
functionality as MCP tools via [FastMCP](https://gofastmcp.com/), mounted on
the **same port** (`8789`) as the REST API — no separate process/port needed.

| Transport | Endpoint |
|---|---|
| Streamable HTTP (recommended) | `http://127.0.0.1:8789/mcp` |
| SSE | `http://127.0.0.1:8789/mcp/sse/` (trailing slash required) |

### Tools

| Tool | Purpose |
|---|---|
| `list_jira_tickets(status?, priority?, project?, q?, limit?)` | List tickets from the local markdown mirror, same filters as `GET /api/jira/tickets`. Read-only. |
| `get_jira_ticket(key)` | Full ticket detail (sections + description_md) for one key, or `None` if not found. |
| `sync_jira()` | Pull latest from Atlassian, rewrite local markdown mirror. Never writes to Atlassian. |
| `jira_status()` | Atlassian reachability + local ticket count. |

The tool implementations in `src/sb_jira/mcp_tools.py` call the exact same
handler functions (`file_store.load_all`, `file_store.apply_filters`,
`file_store.load_by_key`, `sync.run_sync`, `atlassian_client.probe_reachable`)
used by the REST routes in `main.py` — no duplicated business logic, and
results are guaranteed to match between REST and MCP.

### Client config (Cursor / OpenCode / Claude Code)

```json
{
  "mcpServers": {
    "sb-jira": {
      "url": "http://127.0.0.1:8789/mcp",
      "transport": "http"
    }
  }
}
```

If your client only supports SSE transport, use
`"url": "http://127.0.0.1:8789/mcp/sse/"` and `"transport": "sse"` instead.

## Tests

```bash
uv sync
uv run pytest tests/ -q
```

Tests never touch the real `ciq/docs/jira` mirror or real Atlassian —
fixtures and mocks only (see `tests/conftest.py`, `tests/test_api.py`,
`tests/test_mcp.py`).

## launchd

`launchd/com.praspr.sb-jira.plist` runs the service via `uv run` on
`127.0.0.1:8789`. Install with:

```bash
cp launchd/com.praspr.sb-jira.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.praspr.sb-jira.plist
```
