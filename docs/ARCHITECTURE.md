# Architecture

This expands on the README's architecture section with process model,
transports, data model, and internal control flow. Cite source paths are
repo-relative from `sb/`.

## System diagram

```
┌─── Coding Harnesses (Cursor · OpenCode · Claude Code) ────────────────────┐
│  One MCP server named "sb"                                                │
└────────────────────────────┬──────────────────────────────────────────────┘
                              │ HTTP  /mcp  (Streamable HTTP)  or  /sse (SSE)
                              ▼
┌─── sb-core :8787  (127.0.0.1)  — single uvicorn/FastAPI process ─────────┐
│  services/core/src/sb_core/main.py      ASGI host, /health, /webex/login  │
│  services/core/src/sb_core/mcp_app.py   FastMCP "sb", mounts sub-servers  │
│                                                                             │
│  Mounted in-process (no network hop):                                     │
│   - sb_todos.mcp_tools   (todo_* tools)         → todos.db                │
│   - sb_jira.mcp_tools    (list/get/track/sync)  → ciq/docs/jira/tickets/  │
│   - sb_core.chat_tools   (ask_sb)                                          │
│   - sb_core.sync_tools   (sync_adapters, sync_status, search_signals)      │
│   - sb_core.ritual_tools (plan_day, wrap_day, standup, proposals, ...)     │
│   - sb_core.webex_tools  (webex_*, sync_webex, summarize_webex_space)      │
│   - sb_core.skills       (sync_skills, list_skills, get_skill + prompts)   │
│                                                                             │
│  core.db (WAL, FK on, 5s busy timeout, versioned migrations)               │
└────────────────────────────▲───────────────────────────────────────────────┘
                              │ /proxy/mcp (Vite dev proxy)
┌────────────────────────────┴───────────────────────────────────────────────┐
│  sb-web :5173  (Vite + React + TypeScript + Tailwind)                      │
│  Status · Skills · Signals · Today/Wrap/Standup · Todos · JIRA · Webex     │
└──────────────────────────────────────────────────────────────────────────────┘

  sb-webex talks out-of-process to a hosted MCP:
  https://aicoding-mcp-webexapis.cisco.com/mcp/   (public PKCE OAuth, keychain tokens)
```

## Process model

There is exactly one long-running local process: `sb-core`, an
`uvicorn` server hosting a `FastAPI` app
(`services/core/src/sb_core/main.py`). Todos and JIRA are Python
**libraries**, not services — their FastMCP sub-servers are created in
`services/todos/src/sb_todos/mcp_tools.py` and
`services/jira/src/sb_jira/mcp_tools.py`, then mounted onto the parent `sb`
FastMCP instance in `services/core/src/sb_core/mcp_app.py` via `mcp.mount(...)`.
Webex is likewise a library (`services/webex/src/sb_webex/`) whose tools are
wrapped by `sb_core/webex_tools.py` and mounted the same way — but its data
source is an external hosted MCP server reached over HTTPS, not a local
process.

`sb_core/main.py` also rejects all `/api/*` REST paths with 404
(`retired_rest`), by design: domain traffic is MCP-only. There is no
`/api/todos` or `/api/jira` surface.

## Transports

- **Streamable HTTP** at `/mcp` — primary transport for harness MCP clients
  and the web dashboard (via `/proxy/mcp`).
- **SSE** at `/sse` — compatibility transport, same tool surface.
- **`GET /health`** — readiness probe; returns `system_status()` from
  `mcp_app.py` (status, version, database readiness/schema version, and
  tool/prompt/resource counts). Never contacts Atlassian or Webex.
- **`GET /webex/login`** and **`GET /webex/callback`** — plain HTTP redirect
  endpoints (not MCP) that drive the Webex OAuth PKCE flow
  (`services/core/src/sb_core/main.py`).

Both `/mcp` and `/sse` are FastMCP-owned ASGI sub-apps whose routes are
spliced directly onto the FastAPI router (`app.router.routes.extend(...)`) so
the paths stay exact.

## Data model

| Store | Path | Notes |
|---|---|---|
| Core SQLite | `~/.local/share/sb/core.db` | WAL journal, foreign keys on, 5s busy timeout, versioned migration table (`services/core/src/sb_core/store/db.py`). Holds `sb_signals`, `sb_daily` (plan/wrap columns + proposals), `sb_skills`, Webex mirror tables (`sb_webex_meetings`, `sb_webex_spaces`, `sb_webex_messages`). |
| Todos SQLite | `~/.local/share/sb/todos.db` | Independent DB owned by `sb_todos` (`services/todos/src/sb_todos/db.py`); every tool call opens and closes its own connection. Override with `SB_TODOS_DB_PATH`. |
| JIRA mirror | `ciq/docs/jira/tickets/*.md` | Markdown files, one per ticket, written only by `sync_jira`/`track_jira`. Never written to Atlassian. Paths overridable via `SB_JIRA_*` env vars, see `services/jira/src/sb_jira/config.py`. |

Connection policy across the codebase: every MCP tool opens a **fresh**
connection per call and closes it before returning — no process-wide
singleton, no cross-thread sharing (see docstrings in
`sb_core/sync_tools.py`, `sb_core/ritual_tools.py`, `sb_todos/mcp_tools.py`).

## Signal ledger and adapters

`sb_signals` (in `core.db`) is a canonical, UTC-timestamped evidence ledger.
Four adapters populate it, defined in `services/core/src/sb_core/adapters/`:

- `todos.py` — mirrors todo activity from `todos.db`
- `jira.py` — mirrors local JIRA markdown state
- `changelog.py` — mirrors `CHANGELOG.md` entries under configured roots
- `git.py` — mirrors recent commits (filterable by `git_authors`)

`sync_adapters` (in `sb_core/sync_tools.py`) runs adapters in isolated
subprocesses with a bounded timeout (`run_adapter_by_name`, see
`sb_core/adapters/__init__.py`), so one failing adapter never fails the whole
sync. `sync_status` returns last-run state per adapter. `search_signals`
queries the ledger by `q`/`source`/`kind`/`since`; every result carries an
`id` meant to be cited as `[signal:N]` in generated prose (plans, wraps,
standups, `ask_sb` answers).

Note: `sync_tools._ALL_ADAPTERS` includes `"webex"` as a fifth name, but no
`webex.py` adapter module exists under `sb_core/adapters/` — Webex evidence
currently flows through its own mirror tables and `webex_tools.py`, not
through `sb_signals`. Small discrepancy between the adapter name list and
the adapter directory; harmless because `run_adapter_by_name` would simply
error for that name if invoked.

## Skills indexing

`sync_skills` (`services/core/src/sb_core/skills.py`) scans a fixed
allow-list of roots, never the rest of the home directory:

- `<repo>/harness/skills`
- `<repo>/.cursor/skills`
- `~/.cursor/skills`
- `~/.claude/skills`
- any directories listed in `SB_CORE_EXTRA_SKILL_ROOTS`

Each subdirectory whose name matches `_ID_RE` and contains a `SKILL.md` is a
candidate skill. Content identity is SHA-256 of the raw file bytes. Frontmatter
(`name`, `description`) plus an `## Allowed tools` section are parsed; the
procedure body is capped at 32,000 chars. Results are upserted into
`sb_skills`; skills no longer found on disk are marked `available = 0` but
kept in the table (not deleted). On startup (`main.py` lifespan) and after
every `sync_skills` call, `refresh_skill_surface` re-registers enabled +
available skills as MCP prompts (`skill_<id>`) and resources
(`skill://<id>`), and disables ones that dropped out.

## Daily rituals

All implemented in `services/core/src/sb_core/ritual_tools.py` (mounted as
the FastMCP sub-server named `"sb-ritual"`):

- **`plan_day`** — ranks open todos (`sb_core/ranker.py`) against goals
  (`sb_core/goals.py`) and recent signals, persists one row per date in
  `sb_daily.plan_md` / `plan_data`. Does not touch wrap columns. Cached by
  default; pass `refresh=True` to recompute.
- **`wrap_day`** — gathers that date's signals (local-calendar-day UTC
  range), asks the LLM (`sb_core/llm.py`) for a citation-grounded narrative,
  and falls back to a deterministic bullet list if the LLM is unavailable or
  hallucinates a `[signal:N]` id not in the gathered set
  (`_llm_bullets_ok`). With `dry_run=False`, persists the wrap and queues a
  `changelog` proposal (see below).
- **Proposals** — `wrap_day` (non-dry-run) can queue a `kind: "changelog"`
  proposal targeting `<root>/CHANGELOG.md`. `list_proposals` /
  `reject_proposal` are read/no-op; `approve_proposal` is the **only** tool
  that writes to disk, and only after strict path safety
  (`_safe_changelog_target`): exact basename `CHANGELOG.md`, no symlink in
  any path component, resolved path must live under a configured root, size
  caps enforced, and the payload is appended idempotently (skipped if
  already present).
- **`standup`** — deterministic (no LLM), builds 5–8 bullets from today's
  persisted plan, whether yesterday's wrap exists, and today's open P1/P2
  todos plus any meetings for the day.

Note: `services/core/src/sb_core/plan_tools.py` implements an earlier,
functionally-overlapping version of `whoami`/`get_roots`/`get_goals`/
`plan_day`/`get_day` under a separate FastMCP instance (`"sb-plan"`), but it
is **not mounted** anywhere in `mcp_app.py` — only `ritual_tools.mcp` is
mounted. `plan_tools.py` still has a dedicated test file
(`services/core/tests/test_plan_tools.py`) but is dead code from the running
server's perspective. Treat `ritual_tools.py` as the source of truth for
these tool names.

## Web ↔ core

The dashboard never talks to sb-core directly from the browser; Vite's dev
server proxies:

- `/proxy/mcp` → `http://127.0.0.1:8787/mcp` (rewritten to strip the prefix)
- `/proxy/claudegate` → `http://localhost:9999` (GitHub Copilot proxy,
  Anthropic-compatible; used for the Copilot usage tile)
- `/proxy/cursor` → `https://cursor.com`, with the dev server injecting a
  `WorkosCursorSessionToken` cookie read from Cursor.app's local
  `state.vscdb` (`web/vite/cursor-auth.ts`); the browser never sees the
  token

See `web/vite.config.ts` for the exact proxy definitions.

## Security posture

- sb-core binds to `127.0.0.1` only — no LAN exposure.
- Secrets (Atlassian token, Webex OAuth tokens) live only in the macOS
  Keychain under service `sb`; never written to the repo or logs.
- JIRA is architecturally read/pull-only: `sync_jira` and `track_jira` fetch
  from Atlassian and write local markdown; nothing in `sb_jira` writes back
  upstream.
- Webex is architecturally read-only: `sb_webex`/`webex_tools.py` only call
  tools that list/read meetings, spaces, and message previews.
- Skill indexing is allow-listed to specific project/harness directories; it
  never walks the rest of the home directory (`skills.default_roots`).
- The only local filesystem write path outside the SQLite databases and the
  JIRA markdown mirror is `approve_proposal`'s `CHANGELOG.md` append, which is
  gated by the path-safety checks described above.
