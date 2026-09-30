# Getting Started

## Prerequisites

- macOS
- Python 3.13+ and [`uv`](https://docs.astral.sh/uv/) at `~/.local/bin/uv`
- Node 20+ and npm

## Repo layout at a glance

```
sb/
├── web/                    React + TypeScript dashboard (Vite, port 5173)
├── services/
│   ├── core/                sb-core — unified local MCP process (port 8787)
│   ├── todos/                sb-todos — MCP library mounted in-process, SQLite-backed
│   ├── jira/                 sb-jira — read-only MCP library mounted in-process
│   └── webex/                sb-webex — read-only Webex client library mounted in-process
├── docs/
│   ├── status/               Phase 0/1 status snapshots
│   ├── design/               UI design brief, tokens, components, HTML mockup
│   └── (this doc set)
├── harness/skills/           SKILL.md files indexed by sb-core
├── README.md                 Top-level overview
└── PENDING.md                What's next / not built yet
```

See `README.md` for the authoritative service/port table and architecture diagram.

## Bootstrapping the core service

From the repo root:

```bash
cd sb/services/core
uv sync --group dev
uv run uvicorn sb_core.main:app --host 127.0.0.1 --port 8787
```

This starts the single unified MCP process. Todos and JIRA tools are mounted
in-process (no separate servers to start). Webex tools call the hosted MCP
directly once you sign in (see below).

## Installing the launchd job

`com.praspr.sb` is the only sb launchd job. Run these from the repo root:

```bash
# Install and load the unified service
cp services/core/launchd/com.praspr.sb.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb.plist

# Retire the standalone todos and JIRA jobs (if present from an older setup)
launchctl bootout gui/$(id -u)/com.praspr.sb-todos || true
launchctl bootout gui/$(id -u)/com.praspr.sb-jira || true
rm -f ~/Library/LaunchAgents/com.praspr.sb-todos.plist
rm -f ~/Library/LaunchAgents/com.praspr.sb-jira.plist

# Smoke
curl -s http://127.0.0.1:8787/health
```

## Health check

```bash
curl -s http://127.0.0.1:8787/health
```

Returns a privacy-safe readiness summary: `status`, `version`, database
readiness/schema version, and tool/prompt/resource counts. It does not
contact Atlassian or Webex.

## Wiring MCP into your coding harness

One server, named `sb`, is the harness entry. Do not add separate
`sb-todos` / `sb-jira` network servers — they no longer exist standalone.

| Harness | Config file | Entry |
|---|---|---|
| Cursor | `~/.cursor/mcp.json` | one server named `sb` at `http://127.0.0.1:8787/mcp` |
| Claude Code | `~/.claude.json` | one HTTP MCP named `sb` at `http://127.0.0.1:8787/mcp` |
| OpenCode | `~/.config/opencode/opencode.json` | one HTTP MCP named `sb` at `http://127.0.0.1:8787/mcp` |

Remove only previous `sb-todos` / `sb-jira` entries; leave every other
server in those files untouched.

## Running the web dashboard

```bash
cd sb/web
npm install     # first time only
npm run dev     # → http://localhost:5173
```

The dashboard talks to sb-core through the Vite dev proxy at `/proxy/mcp`
(see `docs/WEB_DASHBOARD.md`).

## Optional: Webex sign-in

Webex tools are read-only and require a one-time sign-in:

1. With sb-core running, open `http://127.0.0.1:8787/webex/login` in a browser.
2. Complete the hosted OAuth (PKCE) flow against
   `https://aicoding-mcp-webexapis.cisco.com/mcp/`.
3. Tokens are stored in the macOS Keychain under service `sb`. The browser
   never sees the token.
4. Call `sync_webex` (or use the `/webex` / `/meetings` pages) to pull a
   read-only mirror.

## Optional: Atlassian token for JIRA sync

`sync_jira` only pulls from Atlassian into local markdown; it never writes
back. Store your API token in the macOS Keychain:

```bash
security add-generic-password -s sb -a jira.token -w '<token>'
```

(service `sb`, account/key `jira.token`) or set the `ATLASSIAN_API_TOKEN`
environment variable. Without a token, `sync_jira` returns an error entry and
changes nothing.

## Troubleshooting

- **Port 8787 already in use** — another sb-core instance (or launchd job)
  is likely running. Check `launchctl print gui/$(id -u)/com.praspr.sb` or
  `lsof -i :8787`.
- **launchd bootstrap failed** — confirm the plist was copied to
  `~/Library/LaunchAgents/com.praspr.sb.plist` and that no stale
  `com.praspr.sb-todos` / `com.praspr.sb-jira` jobs are still loaded
  (`launchctl bootout` them first).
- **`uv` not found** — install it per the [uv docs](https://docs.astral.sh/uv/)
  and confirm it resolves at `~/.local/bin/uv`.
- **`/health` returns `degraded`** — the SQLite database at
  `~/.local/share/sb/core.db` could not be opened; check permissions and
  parent directory existence (created automatically on first connection).
- **Web app can't reach MCP** — confirm sb-core is running on `:8787` before
  starting `npm run dev`; the Vite proxy fails silently if the target is down.
