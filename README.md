# sb — Second Brain

A local personal-assistant system. Runs entirely on your Mac, integrates with
your coding harnesses (Claude Code / OpenCode / Cursor / VS Code), and exposes
its own dashboard in the browser.

Everything is optional and modular — take what you want, ignore the rest.

## What's in this repo

```
sb/
├── web/                    React + TypeScript dashboard (Vite, port 5173)
├── services/
│   ├── todos/              sb-todos — MCP + REST service, SQLite-backed
│   └── jira/               sb-jira  — read-only MCP + REST for JIRA
├── docs/
│   ├── status/             Phase 0/1 status snapshots (see docs/status/README.md)
│   └── design/             UI design brief, tokens, components, HTML mockup
├── README.md               ← this file
└── PENDING.md              What's next / not built yet
```

## Live services

| Service | Port | Transport | Storage | Auto-start |
|---|---|---|---|---|
| **sb-todos** | via `sb-core` `:8787` | MCP tools on the unified server | `~/.local/share/sb/todos.db` (SQLite) | no separate job; unload `com.praspr.sb-todos` at cutover |
| **sb-jira** | via `sb-core` `:8787` | pull-only MCP tools on the unified server | markdown files at `ciq/docs/jira/tickets/` | no separate job; unload `com.praspr.sb-jira` at cutover |
| **sb-web** | `127.0.0.1:5173` | HTTP (dev) | dashboard via `/proxy/mcp` | `npm run dev` |

Ports live in the IANA Dynamic/Private range (49152–65535) to avoid collisions
with common dev services.

## Architecture

```
┌─── Coding Harnesses (Cursor · OpenCode · Claude Code) ──────────┐
│  One MCP server named sb                                          │
└────────────────────────────┬──────────────────────────────────────┘
                             │ HTTP  /mcp  or  /sse
                             ▼
┌─── sb-core :8787  (127.0.0.1) ───────────────────────────────────┐
│  Python · FastMCP + FastAPI                                       │
│  core.db  ·  todos.db  ·  local JIRA markdown (pull-only)         │
│  skills · signals · plan · wrap · standup                         │
└────────────────────────────▲──────────────────────────────────────┘
                             │ /proxy/mcp
┌────────────────────────────┴──────────────────────────────────────┐
│  sb-web :5173  (Vite + React + TypeScript + Tailwind)             │
│  Status · Skills · Signals · Today · Wrap · Standup · Todos · JIRA │
└────────────────────────────────────────────────────────────────────┘
```

## Unified core

`services/core` is the single local MCP process. It binds to `127.0.0.1:8787`,
serves Streamable HTTP at `/mcp` and compatibility SSE at `/sse`, and exposes
operational readiness at `GET /health` and in the dashboard at `/status`.
The database defaults to `~/.local/share/sb/core.db` (WAL, foreign keys, a
5-second busy timeout, and a versioned migration table). Todo tools are
mounted in-process under their original names (`todo_list`, `todo_add`,
`todo_complete`, and the rest). JIRA tools (`list_jira_tickets`,
`get_jira_ticket`, `sync_jira`, `jira_status`) are mounted the same way and
only pull Atlassian into local markdown. The dashboard calls both through
`/proxy/mcp`. `GET /health` does not contact Atlassian.

`sync_skills` indexes `*/SKILL.md` from `<repo>/harness/skills`,
`<repo>/.cursor/skills`, `~/.cursor/skills`, `~/.claude/skills`, and any extra
directories in `SB_CORE_EXTRA_SKILL_ROOTS`. It does not scan the rest of the
home directory. Content identity uses SHA-256. The dashboard lists skills at
`/skills`.

Signal adapters (`todos`, `jira`, `changelog`, `git`) write canonical UTC rows
into `sb_signals`. Search them with `search_signals` and cite `[signal:N]`.
The dashboard shows them at `/signals`. `plan_day` ranks open todos into
`sb_daily` plan columns without overwriting wrap. The dashboard shows that
plan at `/today`. `wrap_day` writes the wrap columns and queues a local
CHANGELOG proposal. Approval appends only a `CHANGELOG.md` under a configured
root. The dashboard shows wraps and proposals at `/wrap`. `standup` builds 5–8
bullets from today's plan, the previous day's wrap, and open high-priority
todos. The dashboard shows that at `/standup`.

```bash
cd sb/services/core
uv sync --group dev
uv run uvicorn sb_core.main:app --host 127.0.0.1 --port 8787
```

The dashboard talks to that process through Vite `/proxy/mcp`. Copilot and
Cursor usage proxies stay independent.

### Cutover (prepared, not applied)

Do not load this until todos and JIRA are mounted in-process. The plist is
`services/core/launchd/com.praspr.sb.plist`. Exact commands, run from the repo
root, for the later operational cutover:

```bash
# Install and load the unified service
cp services/core/launchd/com.praspr.sb.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb.plist

# Retire the standalone todos and JIRA jobs
launchctl bootout gui/$(id -u)/com.praspr.sb-todos || true
launchctl bootout gui/$(id -u)/com.praspr.sb-jira || true
rm -f ~/Library/LaunchAgents/com.praspr.sb-todos.plist
rm -f ~/Library/LaunchAgents/com.praspr.sb-jira.plist

# Smoke
curl -s http://127.0.0.1:8787/health
```

Harness MCP entries, leaving every unrelated server untouched:

| Harness | Config | Entry |
|---|---|---|
| Cursor | `~/.cursor/mcp.json` | one server named `sb` at `http://127.0.0.1:8787/sse` (or `/mcp` if the client supports Streamable HTTP) |
| Claude Code | `~/.claude.json` | one HTTP MCP named `sb` at `http://127.0.0.1:8787/mcp` |
| OpenCode | `~/.config/opencode/opencode.json` | one HTTP MCP named `sb` at `http://127.0.0.1:8787/mcp` |

Remove only the previous `sb-todos` and `sb-jira` entries in those files.
Tokens stay in the macOS Keychain (`sb` / `jira.token`) or external config.
No credentials belong in Git.

## How to run

### Prerequisites
- macOS
- Python 3.13+ · [`uv`](https://docs.astral.sh/uv/) at `~/.local/bin/uv`
- Node 20+ · npm

### Web dashboard

```bash
cd sb/web
npm install     # first time only
npm run dev     # → http://localhost:5173
```

### Core service

Run `sb-core` with the commands in [Unified core](#unified-core). Login
auto-start is the plist documented under **Cutover (prepared, not applied)**.
Those commands are not applied by this repository. The standalone todos and
JIRA launchd plists are no longer in the repo.

## MCP tools

One server, `sb`, is the harness entry. The cutover table above is the
config to apply later. Do not add `sb-todos` or `sb-jira` network servers.

### sb-todos tools (write-capable)

| Tool | What it does |
|---|---|
| `todo_list` | List todos, filter by status/priority/domain/tag |
| `todo_get` | Get one todo by id |
| `todo_add` | Create a new todo (idempotent on external_source+external_ref) |
| `todo_complete` | Mark complete |
| `todo_uncomplete` | Un-mark |
| `todo_update` | Update any field |
| `todo_delete` | Delete a todo |
| `todo_search` | Substring search on title + description |

### sb-jira tools (read-only)

| Tool | What it does |
|---|---|
| `list_jira_tickets` | List tickets, filter by status/priority/project/q |
| `get_jira_ticket` | Get one ticket by key, full detail with sections |
| `sync_jira` | Pull from Atlassian → rewrite local markdown files (never writes up) |
| `jira_status` | Atlassian reachability + ticket count |

## The web app

`sb/web` is a Vite/React/TypeScript app matching a Linear-dense design language
(see `sb/docs/design/`).

Five pages, five sidebar items:

| Route | Data | Status |
|---|---|---|
| `/` — Landing | Usage tiles (Copilot + Cursor) · Today's todos · Today's meetings | tiles + todos live · meetings mock |
| `/todos` | sb-todos SQLite (add + complete work end-to-end) | live |
| `/jira` | sb-jira, 24 real tickets from `ciq/docs/jira/tickets/` | live |
| `/meetings` | Mock data | placeholder |
| `/webex` | Mock data | placeholder |

Shortcuts: `⌘K` opens the command palette, `⌘N` jumps to `/todos` and focuses
the quick-add input.

## Config files

| Purpose | Path |
|---|---|
| Todos SQLite | `~/.local/share/sb/todos.db` |
| Todos launchd | `~/Library/LaunchAgents/com.praspr.sb-todos.plist` |
| JIRA launchd | `~/Library/LaunchAgents/com.praspr.sb-jira.plist` |
| Todos logs | `/tmp/sb-todos.{out,err}.log` |
| JIRA logs | `/tmp/sb-jira.{stdout,stderr}.log` |
| Atlassian token (optional, read-only) | macOS Keychain, service `sb`, key `jira.token` |

## LLM access

The web app's Copilot and Cursor usage tiles use existing local services:

- **claudegate** at `http://localhost:9999` — GitHub Copilot proxy (Anthropic-compatible)
- **Cursor** — the Vite dev proxy reads Cursor.app's own JWT from `state.vscdb`
  and builds the `WorkosCursorSessionToken` cookie server-side. The browser
  never sees the token. Zero config as long as you're signed in to Cursor.app.

## Design language

Dark-first Linear-inspired UI. Full token spec + component catalog at
`sb/docs/design/`. There's a fully rendered HTML mockup at
`sb/docs/design/mockups/today-view.html` if you want to see it before running
the app.

## Where to look next

- `sb/PENDING.md` — what's not built yet, with recommended order
- `sb/docs/status/` — historical Phase 0/1 snapshots and design decisions
- `sb/docs/design/` — full design brief, component catalog, HTML mockup
- Individual service READMEs at `sb/services/todos/README.md` and `sb/services/jira/README.md`
