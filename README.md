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
│   ├── core/                sb-core — unified local MCP process (port 8787)
│   ├── todos/                sb-todos — MCP library mounted in-process, SQLite-backed
│   ├── jira/                 sb-jira — read-only MCP library mounted in-process
│   ├── webex/                sb-webex — Webex client library mounted in-process
│   └── cli/                  sb-cli — `sb` command-line client (log/context/search/projects)
├── docs/
│   ├── status/               Phase 0/1 status snapshots (see docs/status/README.md)
│   ├── design/                UI design brief, tokens, components, HTML mockup
│   └── (GETTING_STARTED.md, ARCHITECTURE.md, SERVICES.md, MCP_TOOLS.md,
│         WEB_DASHBOARD.md, DEVELOPMENT.md — see docs/README.md)
├── harness/skills/            SKILL.md files indexed by sb-core
├── README.md                  ← this file
└── PENDING.md                 What's next / not built yet
```

## Live services

| Service | Port | Transport | Storage | Auto-start |
|---|---|---|---|---|
| **sb-core** | `127.0.0.1:8787` | MCP at `/mcp`, SSE at `/sse`, `GET /health` | `~/.local/share/sb/core.db` (SQLite) | launchd `com.praspr.sb` |
| **sb-todos** | via `sb-core` `:8787` | MCP tools on the unified server | `~/.local/share/sb/todos.db` (SQLite) | runs inside `sb-core` |
| **sb-jira** | via `sb-core` `:8787` | pull-only MCP tools on the unified server | markdown files at `ciq/docs/jira/tickets/` | runs inside `sb-core` |
| **sb-webex** | via `sb-core` `:8787` (+ hosted MCP over HTTPS) | MCP tools on the unified server | mirror tables in `core.db` | runs inside `sb-core` |
| **sb-web** | `127.0.0.1:5173` | HTTP (dev) | dashboard via `/proxy/mcp` | `npm run dev` |
| **sb CLI** | n/a | calls `sb-core` over `/mcp` | none (stateless client) | `sb log` / `sb context` / `sb search` / `sb projects` |

Ports live in the IANA Dynamic/Private range (49152–65535) to avoid collisions
with common dev services.

## Architecture

```
┌─── Coding Harnesses (Cursor · OpenCode · Claude Code) ────────────────────────┐
│  One MCP server named sb                                                       │
└────────────────────────────┬────────────────────────────────────────────────────┘
                              │ HTTP  /mcp  or  /sse
                              ▼
┌─── sb-core :8787  (127.0.0.1) ────────────────────────────────────────────────┐
│  Python · FastMCP + FastAPI · ~79 tools (prompts/resources per skill index)     │
│  core.db · todos.db · local JIRA markdown (pull-only) · Webex mirror           │
│  skills · signals · ledger (append-only) · reports · triage · goals · scheduler│
└────────────────────────────▲────────────────────────────────────────────────────┘
                              │ /proxy/mcp
┌────────────────────────────┴────────────────────────────────────────────────────┐
│  sb-web :5173  (Vite + React + TypeScript + Tailwind)                          │
│  Landing · Attention · Goals · Reports · Ledger · Proposals ·                  │
│  Todos · JIRA · Meetings · Webex · Skills · Signals                            │
└────────────────────────────────────────────────────────────────────────────────┘

  sb CLI (services/cli) talks to the same /mcp endpoint, no browser required.
```

## Unified core

`services/core` is the single local MCP process. It binds to `127.0.0.1:8787`,
serves Streamable HTTP at `/mcp` and compatibility SSE at `/sse`, and exposes
operational readiness at `GET /health` (live tool/prompt/resource counts;
~79 tools as of this writing, with prompt/resource counts depending on the
indexed skill surface). The database defaults to `~/.local/share/sb/core.db`
(WAL, foreign keys, a 5-second busy timeout, and a versioned migration table,
currently at schema version 12). Todo tools are mounted in-process under
their original names (`todo_list`, `todo_add`, `todo_complete`, and the
rest, now including goal/JIRA/recurrence fields — see below). JIRA tools
(`list_jira_tickets`, `get_jira_ticket`, `track_jira`, `untrack_jira`,
`sync_jira`, `jira_status`) are mounted the same way and only pull Atlassian
into local markdown. The dashboard calls all of this through `/proxy/mcp`.
`GET /health` does not contact Atlassian or Webex.

`sync_skills` indexes `*/SKILL.md` from `<repo>/harness/skills`,
`<repo>/.cursor/skills`, `~/.cursor/skills`, `~/.claude/skills`, and any extra
directories in `SB_CORE_EXTRA_SKILL_ROOTS`. It does not scan the rest of the
home directory. Content identity uses SHA-256. The dashboard lists skills at
`/skills`.

Signal adapters (`todos`, `jira`, `changelog`, `git`) write canonical UTC rows
into `sb_signals`. Search them with `search_signals` and cite `[signal:N]`.
The dashboard shows them at `/signals`. `plan_day` ranks open todos into
`sb_daily` plan columns without overwriting wrap; `wrap_day` writes the wrap
columns and queues a local CHANGELOG proposal; `standup` builds 5–8 bullets
from today's plan, the previous day's wrap, and open high-priority todos.
These daily rituals are now surfaced as sub-tabs on the dashboard's
**Reports** page (`/reports`) rather than standalone routes — see
[Reports, Ledger, and Proposals](#reports-ledger-and-proposals) below.

The scheduler runs inside `sb-core` and is ticked externally every five
minutes by the `com.praspr.sb-scheduler` launchd job, which POSTs
`run_due_schedules` over `/mcp`. Schedules (name, ritual, 5-field cron,
enabled flag) are managed in Settings → Schedules or via
`add_scheduled_ritual` / `list_scheduled_rituals` / `delete_scheduled_ritual`.
A separate `com.praspr.sb-morning-open` job opens the dashboard once per day.

```bash
cd sb/services/core
uv sync --group dev
uv run uvicorn sb_core.main:app --host 127.0.0.1 --port 8787
```

The dashboard talks to that process through Vite `/proxy/mcp`. Copilot and
Cursor usage proxies stay independent.

## The narrative ledger

`sb_ledger` is an append-only evidence ledger, separate from the signal
adapters. Rows can never be updated or deleted — `sb_core/store/db.py`'s
`_m8_ledger` migration installs `BEFORE UPDATE`/`BEFORE DELETE` triggers that
raise `sqlite3.IntegrityError('sb_ledger is append-only')`; corrections are
new rows with `action_verb='Corrected'`. Every entry is deterministically
redacted before it is written (`sb_core/ledger_redact.py`; secrets are
replaced with `[REDACTED:<KIND>]`, never rejected, and stamped with a
`redaction_rules_version`). A composite session id groups related entries
from the same agent/project/working-dir within a 30-minute window
(`sb_core/ledger_session.py`).

Ledger rows dual-write to per-project `CHANGELOG.md` files
(`sb_core/ledger_sync.py`): a bullet like
`- **14:32:07 UTC** · **Debugged** APISIX 401 … — *`scope`*` is inserted as
the first line under that day's `## [YYYY-MM-DD]` heading, guarded by an
flock lock so concurrent writers never corrupt the file. The project
registry (`sb_project_registry`) is seeded on first run with exactly two
entries — `ciq` and `sb` — both `sync_mode='dual'`; no other repo is
auto-enrolled. Enroll more via Settings → Projects or `sb projects enroll`.

Query the ledger with `ledger_search`/`ledger_context`/`ledger_by_ref`, or
log to it directly with `ledger_log`/`ledger_batch_log` (see
`docs/MCP_TOOLS.md` for the full sb-ledger tool list). The dashboard shows it
at `/ledger`.

## sb CLI

`services/cli` is a thin command-line client (`httpx` + `argparse`, no other
dependencies) that talks to the same `sb-core` `/mcp` endpoint:

```bash
cd sb/services/cli
uv sync --group dev

sb log "Shipped the ledger foundation" --project sb --verb Shipped
sb context --project sb --since 48h
sb search "APISIX" --project sb
sb projects list
sb projects enroll --project demo --path /abs/path --sync-mode dual
```

`sb log` auto-derives `agent` from `$SB_AGENT` (default `"cli"`), `working_dir`
from `os.getcwd()`, and tags entries `source_harness="sb-log-cli"`. Exit
codes are nonzero only on transport failures; an idempotent no-op ("already
recorded") exits 0.

### Login service

`com.praspr.sb` is the primary sb launchd job; two supporting jobs ship
alongside it. Plists live in `services/core/launchd/`:

```bash
# Install and load the unified service
cp services/core/launchd/com.praspr.sb.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb.plist

# Install the morning-open (once/day) and scheduler (every 5 min) jobs
cp services/core/launchd/com.praspr.sb-morning-open.plist ~/Library/LaunchAgents/
cp services/core/launchd/com.praspr.sb-scheduler.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb-morning-open.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb-scheduler.plist

# Retire the standalone todos and JIRA jobs (older installs only)
launchctl bootout gui/$(id -u)/com.praspr.sb-todos || true
launchctl bootout gui/$(id -u)/com.praspr.sb-jira || true
rm -f ~/Library/LaunchAgents/com.praspr.sb-todos.plist
rm -f ~/Library/LaunchAgents/com.praspr.sb-jira.plist

# Smoke
curl -s http://127.0.0.1:8787/health
```

See `services/core/launchd/README.md` for the full install/bootout reference,
including what each job's `StartInterval`/`StartCalendarInterval` does.

Harness MCP entries, leaving every unrelated server untouched:

| Harness | Config | Entry |
|---|---|---|
| Cursor | `~/.cursor/mcp.json` | one server named `sb` at `http://127.0.0.1:8787/mcp` |
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
auto-start is the plist documented under **Login service**. Restart it with
`launchctl kickstart -k gui/$(id -u)/com.praspr.sb` any time schema or tool
code changes. Skill prompts and resources are restored from the stored index
at startup.

## MCP tools

One server, `sb`, is the harness entry, configured as in the table above.
Do not add `sb-todos` or `sb-jira` network servers. The full reference (all
76 tools, grouped by submount) is in `sb/docs/MCP_TOOLS.md`; the tables below
cover the two domain services most harnesses call directly.

### sb-todos tools (write-capable)

| Tool | What it does |
|---|---|
| `todo_list` | List todos, filter by status/priority/domain/tag |
| `todo_get` | Get one todo by id |
| `todo_add` | Create a new todo (idempotent on external_source+external_ref); accepts `goal_id`, `jira_ref`, `recurrence_rule`, `parent_todo_id` |
| `todo_complete` | Mark complete; auto-materializes the next instance if the todo has a `recurrence_rule` |
| `todo_uncomplete` | Un-mark |
| `todo_update` | Update any field, including `goal_id`/`jira_ref`/`recurrence_rule`/`parent_todo_id` |
| `todo_delete` | Delete a todo |
| `todo_search` | Substring search on title + description |
| `expand_recurring_todo` | Manually materialize the next instance of a recurring todo (same engine `todo_complete` calls automatically) |

`recurrence_rule` is an RRULE-lite string: `FREQ=DAILY`, `FREQ=WEEKLY;BYDAY=MO,WE`,
or `FREQ=MONTHLY;BYMONTHDAY=1`. `jira_ref` links a todo to a JIRA key (also
populated automatically by `bulk_import_jira_to_todos`, see below). `goal_id`
points at a row in the DB-backed goals registry (`sb_goals_registry`).

### sb-jira tools (read-only against Atlassian)

| Tool | What it does |
|---|---|
| `list_jira_tickets` | List tickets, filter by status/priority/project/q |
| `get_jira_ticket` | Get one ticket by key, full detail with sections |
| `track_jira` | Fetch one ticket by key/browse link and keep it tracked across syncs |
| `untrack_jira` | Stop refreshing a tracked ticket (local file is kept) |
| `sync_jira` | Pull from Atlassian → rewrite local markdown files (never writes up) |
| `jira_status` | Atlassian reachability + ticket count |

`bulk_import_jira_to_todos` (a separate submount, see `docs/MCP_TOOLS.md`)
creates a todo per matching local-mirror ticket in one call, mapping JIRA
priority (Highest→1 … Lowest→4) onto todo priority.

## The web app

`sb/web` is a Vite/React/TypeScript app matching a Linear-dense design
language (see `sb/docs/design/`). The landing page combines usage,
operational charts, a Morning Brief dialog, and a read-only cited chat over
local second-brain data.

| Route | Data | Status |
|---|---|---|
| `/` — Landing | Usage tiles · charts · Morning Brief · cited local chat | live |
| `/attention` | Ranked Webex mentions/DMs/replies-to-me, with one-click log-to-ledger | live after sign-in and sync |
| `/goals` | DB-backed goals by tier, alignment heatmap, drift alerts | live |
| `/reports` | Daily/Weekly/Monthly/Query ledger reports, plus Today/Wrap/Standup sub-tabs, Post-to-Webex and Email-draft actions | live |
| `/ledger` | Append-only ledger table + timeline, full-text search | live |
| `/proposals` | Pending CHANGELOG (and meeting-note) proposals, approve/reject | live |
| `/skills` | Indexed project and system skills | live |
| `/signals` | Local evidence ledger and adapter state | live |
| `/todos` | sb-todos SQLite, with goal/JIRA/recurrence pickers and a bulk-JIRA-import action | live |
| `/jira` | pull-only JIRA mirror, plus tracked keys from a pasted link | live |
| `/meetings` | Mirrored Webex meetings, a pre-meeting context card, and a "Propose notes" action | live after sign-in and sync |
| `/webex` | Filtered attention, spaces (with mute/unmute), and cited space summaries | live after sign-in and sync |

Standalone `/today`, `/wrap`, `/standup`, and `/status` routes from earlier
phases have been retired: the rituals are now `/reports` sub-tabs, and
status/diagnostics moved into the Settings popover (Connections +
Diagnostics + Projects + Sessions + Schedules tabs).

Webex uses the hosted MCP at `https://aicoding-mcp-webexapis.cisco.com/mcp/`
for reads, plus the standard Webex REST API (same bearer token) for two
single-resource lookups (`/people/me`, `/messages/{id}`) used to detect
replies to your own messages. Sign in once at
`http://127.0.0.1:8787/webex/login`. The client is public PKCE; tokens stay
in the macOS keychain under service `sb`. On first sync after sign-in,
`sync_webex` captures your identity (email + display name) into
`sb_webex_identity` and caches it — later syncs reuse the cached identity.
Sync is otherwise manual and read-only, except for one explicit,
write-capable tool, `webex_post_message`, used only by the dashboard's
**Post to Webex** report action. Python trusts the Cisco certificate chain
through the operating-system store.

Shortcuts: `⌘K` opens the command palette (supports slash commands —
`/plan`, `/wrap`, `/standup`, `/brief`, `/goals`, `/attention`, `/ledger <q>`
— and a URL smart-handler for pasted JIRA/GitHub/Webex/file links), `⌘N`
jumps to `/todos` and focuses the quick-add input.

## Config files

| Purpose | Path |
|---|---|
| Core SQLite | `~/.local/share/sb/core.db` |
| Todos SQLite | `~/.local/share/sb/todos.db` |
| Core launchd | `~/Library/LaunchAgents/com.praspr.sb.plist` |
| Morning-open / scheduler launchd | `~/Library/LaunchAgents/com.praspr.sb-morning-open.plist`, `com.praspr.sb-scheduler.plist` |
| Core logs | `/tmp/sb.{out,err}.log` (+ `/tmp/sb-morning-open.*`, `/tmp/sb-scheduler.*`) |
| Atlassian token (optional, read-only) | macOS Keychain, service `sb`, key `jira.token` |
| Webex OAuth tokens | macOS Keychain, service `sb` (`webex.access_token`, `webex.refresh_token`, `webex.client_id`) |

## LLM access

The web app's Copilot and Cursor usage tiles use existing local services:

- **claudegate** at `http://localhost:9999` — GitHub Copilot proxy (Anthropic-compatible)
- **Cursor** — the Vite dev proxy reads Cursor.app's own JWT from `state.vscdb`
  and builds the `WorkosCursorSessionToken` cookie server-side. The browser
  never sees the token. Zero config as long as you're signed in to Cursor.app.

`sb-core`'s own LLM calls (wrap narration, report query narration, meeting
note drafts) go through the same claudegate proxy via `sb_core/llm.py`. The
default model is `SB_CORE_LLM_MODEL=claude-haiku-4.5-low`; override it with
that environment variable (or the `llm_model` key in
`~/.config/sb/config.yaml`) to use a different claudegate-served model.
Every LLM-backed tool validates citations against the supplied context and
falls back to a deterministic, non-LLM result if the backend is unavailable
or a citation doesn't match.

## Design language

Dark-first Linear-inspired UI. Full token spec + component catalog at
`sb/docs/design/`. There's a fully rendered HTML mockup at
`sb/docs/design/mockups/today-view.html` if you want to see it before running
the app.

## Where to look next

- `sb/docs/README.md` — index of the deeper doc set (architecture, services,
  MCP tools, web dashboard, development)
- `sb/PENDING.md` — what's not built yet, with recommended order (note: parts
  of it predate the unified `sb-core` rollout — see `docs/DEVELOPMENT.md`)
- `sb/docs/status/` — historical Phase 0/1 snapshots and design decisions
- `sb/docs/design/` — full design brief, component catalog, HTML mockup
- Individual service READMEs at `sb/services/todos/README.md`,
  `sb/services/jira/README.md`, and `sb/services/cli/README.md`
