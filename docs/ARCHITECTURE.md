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
│  Mounted in-process (no network hop), 76 tools total:                     │
│   - sb_todos.mcp_tools     (todo_*, expand_recurring_todo)  → todos.db     │
│   - sb_jira.mcp_tools      (list/get/track/untrack/sync)    → tickets/*.md │
│   - sb_core.chat_tools     (ask_sb)                                        │
│   - sb_core.sync_tools     (sync_adapters, sync_status, search_signals)    │
│   - sb_core.ritual_tools   (plan_day, wrap_day, standup, proposals, ...)   │
│   - sb_core.skills         (sync_skills, list_skills, get_skill + prompts) │
│   - sb_core.ledger_tools   (ledger_log, ledger_search, sync_ledger_...)    │
│   - sb_core.reports_tools  (report_daily/weekly/monthly/query)            │
│   - sb_core.triage_tools   (webex_attention_*, pre_meeting_context, ...)   │
│   - sb_core.goals_tools    (list/add/update/archive_goal, heatmap, ...)    │
│   - sb_core.scheduler      (add/list/delete_scheduled_ritual, run_due_...) │
│   - sb_core.url_hints      (parse_url_hint)                                │
│   - sb_core.jira_bulk      (bulk_import_jira_to_todos)                     │
│   - sb_core.webex_mute     (mute_space, unmute_space, list_muted_spaces)   │
│   - sb_core.webex_post     (webex_post_message — the one write path)      │
│   - sb_core.webex_tools    (webex_*, sync_webex, webex_rethread, ...)      │
│                                                                             │
│  core.db (WAL, FK on, 5s busy timeout, versioned migrations, schema v10)   │
└────────────────────────────▲───────────────────────────────────────────────┘
                              │ /proxy/mcp (Vite dev proxy)
┌────────────────────────────┴───────────────────────────────────────────────┐
│  sb-web :5173  (Vite + React + TypeScript + Tailwind)                      │
│  Landing · Attention · Goals · Reports · Ledger · Proposals ·              │
│  Todos · JIRA · Meetings · Webex · Skills · Signals                        │
└──────────────────────────────────────────────────────────────────────────────┘

  sb-webex talks out-of-process to a hosted MCP (reads) and the standard
  Webex REST API (two single-resource lookups, same bearer token):
  https://aicoding-mcp-webexapis.cisco.com/mcp/   (public PKCE OAuth, keychain tokens)
  https://webexapis.com/v1/{people/me, messages/{id}}

  sb CLI (services/cli) hits the same /mcp endpoint directly, no browser.
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
wrapped by `sb_core/webex_tools.py`, `sb_core/webex_mute.py`, and
`sb_core/webex_post.py`, then mounted the same way — but its data source is
an external hosted MCP server plus the standard Webex REST API reached over
HTTPS, not a local process. `services/cli` is a separate, stateless Python
package (`sb-cli`) that speaks the same `/mcp` JSON-RPC protocol as any other
harness; it is not mounted into `sb-core` and has no server of its own.

`sb_core/main.py` also rejects all `/api/*` REST paths with 404
(`retired_rest`), by design: domain traffic is MCP-only. There is no
`/api/todos` or `/api/jira` surface.

## Transports

- **Streamable HTTP** at `/mcp` — primary transport for harness MCP clients,
  the web dashboard (via `/proxy/mcp`), and the `sb` CLI.
- **SSE** at `/sse` — compatibility transport, same tool surface.
- **`GET /health`** — readiness probe; returns `system_status()` from
  `mcp_app.py` (status, version, database readiness/schema version, and
  tool/prompt/resource counts — 76 tools / 20 prompts / 20 resources as of
  schema version 10). Never contacts Atlassian or Webex.
- **`GET /webex/login`** and **`GET /webex/callback`** — plain HTTP redirect
  endpoints (not MCP) that drive the Webex OAuth PKCE flow
  (`services/core/src/sb_core/main.py`).
- **`GET /_ui`, `/_ui/`, `/_ui/{path}`** — serve the built web dashboard
  (`web/dist/`, resolved from `settings.web_dist_path` / env `SB_WEB_DIST_PATH`)
  same-origin. Unknown `/_ui/*` subpaths fall back to `index.html` for
  client-side routing; a missing build returns a 503 placeholder without
  affecting the MCP routes. This lets the single launchd `com.praspr.sb`
  process serve both the MCP transports and the production UI in parallel.
- **`GET /proxy/claudegate/{path}`** and **`GET /proxy/cursor/{path}`** —
  same-origin usage passthroughs (httpx) that mirror the Vite dev proxies so
  the Copilot/Cursor usage tiles work when the UI is served from sb-core. The
  Cursor `WorkosCursorSessionToken` cookie is built server-side by
  `sb_core/cursor_auth.py` (stdlib port of `web/vite/cursor-auth.ts`), read
  from Cursor.app's `state.vscdb`, cached 5 minutes, failing soft; the browser
  never sees the token.

Both `/mcp` and `/sse` are FastMCP-owned ASGI sub-apps whose routes are
spliced directly onto the FastAPI router (`app.router.routes.extend(...)`) so
the paths stay exact.

## Data model

| Store | Path | Notes |
|---|---|---|
| Core SQLite | `~/.local/share/sb/core.db` | WAL journal, foreign keys on, 5s busy timeout, versioned migration table (`services/core/src/sb_core/store/db.py`, schema version 10). Holds `sb_signals`, `sb_daily` (plan/wrap columns + proposals), `sb_skills`, `sb_ledger` (+ FTS5 mirror, sessions, project registry), `sb_scheduled_rituals`, `sb_goals_registry`, Webex mirror tables (`sb_webex_meetings`, `sb_webex_spaces` incl. `muted`, `sb_webex_messages` incl. `parent_message_id`/`parent_sender_email`/`is_reply_to_me`), and `sb_webex_identity`. |
| Todos SQLite | `~/.local/share/sb/todos.db` | Independent DB owned by `sb_todos` (`services/todos/src/sb_todos/db.py`); every tool call opens and closes its own connection. Override with `SB_TODOS_DB_PATH`. Schema now includes `goal_id`, `jira_ref`, `recurrence_rule`, `parent_todo_id` (migration `002_batch_columns.sql`). |
| JIRA mirror | `ciq/docs/jira/tickets/*.md` | Markdown files, one per ticket, written only by `sync_jira`/`track_jira`. Never written to Atlassian. Paths overridable via `SB_JIRA_*` env vars, see `services/jira/src/sb_jira/config.py`. A separate `tracking.py` module persists which keys stay tracked across syncs. |

Connection policy across the codebase: every MCP tool opens a **fresh**
connection per call and closes it before returning — no process-wide
singleton, no cross-thread sharing (see docstrings in
`sb_core/sync_tools.py`, `sb_core/ritual_tools.py`, `sb_todos/mcp_tools.py`).

## Signal ledger and adapters

`sb_signals` (in `core.db`) is a canonical, UTC-timestamped evidence ledger
— distinct from the append-only narrative ledger below despite the similar
name (this one is upserted, not append-only). Four adapters populate it,
defined in `services/core/src/sb_core/adapters/`:

- `todos.py` — mirrors todo activity from `todos.db`
- `jira.py` — mirrors local JIRA markdown state
- `changelog.py` — mirrors `CHANGELOG.md` entries under configured roots, and
  (new in Phase 0) auto-promotes any dated, narrative-format bullet under a
  registered project's root into the narrative ledger (`sb_ledger`) via
  `_promote_to_ledger` — see "Ledger auto-promotion" below
- `git.py` — mirrors recent commits (filterable by `git_authors`)

`sync_adapters` (in `sb_core/sync_tools.py`) runs adapters in isolated
subprocesses with a bounded timeout (`run_adapter_by_name`, see
`sb_core/adapters/__init__.py`), so one failing adapter never fails the whole
sync. `sync_status` returns last-run state per adapter. `search_signals`
queries the ledger by `q`/`source`/`kind`/`since`; every result carries an
`id` meant to be cited as `[signal:N]` in generated prose (plans, wraps,
standups, `ask_sb` answers).

Note (still true): `sync_tools._ALL_ADAPTERS` includes `"webex"` as a fifth
name, but no `webex.py` adapter module exists under `sb_core/adapters/` —
Webex evidence flows through its own mirror tables and `webex_tools.py`, not
through `sb_signals`. Small discrepancy between the adapter name list and the
adapter directory; harmless because `run_adapter_by_name` would simply error
for that name if invoked.

## The narrative ledger (append-only)

`sb_ledger` (migration `_m8_ledger` in `store/db.py`) is a separate,
deliberately append-only evidence store, meant to capture cross-harness
narrative activity ("what did any agent, in any session, actually do") —
not just the four structured signal sources above.

**Append-only guarantee.** Two `BEFORE UPDATE`/`BEFORE DELETE` triggers
(`sb_ledger_no_update`, `sb_ledger_no_delete`) call `RAISE(ABORT, 'sb_ledger
is append-only')`; in Python this surfaces as `sqlite3.IntegrityError`, not
`OperationalError` (a detail every test in `test_ledger_append_only.py`
asserts on). Corrections are new rows with `action_verb='Corrected'`
referencing the row being corrected — there is no other way to fix a ledger
entry. An `AFTER INSERT` trigger (`sb_ledger_ai`) mirrors every new row into
an FTS5 virtual table (`sb_ledger_fts`, `tokenize='porter'`) for full-text
search via `search_ledger(q=...)`.

**Redaction.** Every entry is deterministically redacted before it is
persisted (`services/core/src/sb_core/ledger_redact.py`). Rules run
specific-before-generic (AWS keys/secrets, bearer tokens, JWTs, basic-auth
URLs, `ENV=value` secrets, LangSmith keys, then a generic 40+-char hex string
*only* when preceded by a secret-ish keyword within 20 chars, to avoid
flagging ordinary commit SHAs). Matches are replaced with
`[REDACTED:<KIND>]`; the row is stamped `redaction_applied=1` and
`redaction_rules_version=REDACTION_RULES_VERSION` (currently `1`). Content is
**never rejected** over what it contains — it is always redacted and
persisted.

**Session model.** `services/core/src/sb_core/ledger_session.py` derives a
composite session id: `{ISO-UTC-ts}_{agent}_{project}_{short_hash(dir)}_
{short_hash(extras)}`. `resolve_session_id` reuses the most recent session
for the same `(agent, project, working_dir)` tuple if it started within the
last 30 minutes, so a single agentic run's many tool calls land under one
session id instead of minting a fresh one per call; otherwise it derives (and
persists, write-once via `INSERT OR IGNORE`) a new one.

**Dual-write protocol.** `services/core/src/sb_core/ledger_sync.py` writes
every new ledger entry to both SQLite and (for projects registered with
`sync_mode='dual'`) that project's `CHANGELOG.md`. The rendered bullet format
is:

```
- **HH:MM:SS UTC** · **Verb** Summary [links…] — *`scope`*
```

`append_to_changelog` finds or creates today's `## [YYYY-MM-DD]` heading
(inserted directly below an existing `## Unreleased` section if the file
uses that convention, otherwise above the most recent dated heading, or at
the top under the title if there are no dated headings yet), inserts the new
bullet as the *first* line under that heading, and never touches any other
byte of the file. Concurrent writers are serialized with an `flock` on
`<changelog_path>.lock`. `sync_ledger_from_files` is the reverse direction:
it parses bullets already present in a project's `CHANGELOG.md` and
back-fills any that are missing from `sb_ledger` (idempotent via
`content_sha256`); it never writes to files.

The project registry (`sb_project_registry`) is seeded on first run with
exactly two rows — `ciq` and `sb`, both `sync_mode='dual'` — and never
auto-enrolls anything else (`config.py::seed_registry_if_empty`, invoked from
`mcp_app._mount_domains`).

**Ledger auto-promotion.** The `changelog` signal adapter (see above) also
promotes narrative bullets it finds under a *registered* project's
`CHANGELOG.md` into `sb_ledger` (`origin='adapter-promote'`,
`source_harness='changelog-adapter'`), so a bullet appended by any external
means (a hand-edit, a different tool) still lands in the ledger the next
time `sync_adapters` runs — not just entries written through `ledger_log`.

Query the ledger with `ledger_search` / `ledger_context` / `ledger_by_ref` /
`ledger_open_threads`; write with `ledger_log` / `ledger_batch_log`; manage
the registry with `ledger_projects` / `ledger_register_project`. All nine
tools are mounted as the `"sb-ledger"` FastMCP sub-server
(`services/core/src/sb_core/ledger_tools.py`).

Known pre-existing gap (not yet fixed): `search_ledger`'s FTS5 `MATCH` query
mis-parses a bare hyphenated search term (e.g. `"nonexistent-topic"` raises
`sqlite3.OperationalError: no such column: topic`) because FTS5's default
query syntax treats an unescaped `-` specially. Callers should avoid
hyphenated terms in `q` until this is fixed; a single-word or quoted query
works fine.

## Reports

`services/core/src/sb_core/reports/templates.py` builds four markdown
reports directly over the ledger (`daily`, `weekly`, `monthly`, `query`),
mounted as MCP tools in `reports_tools.py` (`report_daily`, `report_weekly`,
`report_monthly`, `report_query`). All four are deterministic by default —
`query` is the only one that may additionally ask the LLM to narrate the
matched rows into a paragraph citing `[ledger:N]`; any hallucinated or
missing citation falls back to the same citation-only listing every other
report uses. `daily`/`weekly`/`monthly` also append an "Open threads"
section using `ledger_open_threads` (ledger entries referencing a still-open
JIRA ticket or todo). The dashboard's `/reports` page also folds in the
pre-existing Today/Wrap/Standup rituals as sub-tabs (see "Daily rituals"
below) so all ritual and ledger reporting lives behind one route.

## Comms triage

`services/core/src/sb_core/triage_tools.py` (mounted as `"sb-triage"`) ranks
the local Webex mirror for attention: `webex_attention_ranked` and
`webex_attention_filtered` (the muted-spaces-excluded variant) both funnel
through a shared `_decorate_attention` helper that classifies each message
via `_triage_kind` into exactly one of three kinds — `"mention"`, `"dm"`, or
`"reply-to-me"` — and **drops** anything that doesn't qualify (there is no
catch-all "message" bucket; this was tightened across Phase 1.5 → 2c).
`pre_meeting_context` and `propose_meeting_notes` build best-effort context
(recent messages/ledger entries/todos that overlap a meeting's attendees or
title keywords) and LLM-drafted ledger/todo proposals respectively, falling
back to a deterministic single-entry draft if the LLM is unavailable. The
dashboard surfaces this at `/attention` (ranked inbox with one-click "Log to
ledger") and on `/meetings` (a pre-meeting context card that shows itself
automatically within 15 minutes of a meeting, plus a "Propose notes" action
on past meetings).

## Webex thread-reply detection

Phase 2c added `"reply-to-me"` as the third attention kind, requiring:

- **Identity capture**: `services/webex/src/sb_webex/client.py::get_me()`
  hits the standard Webex REST API (`https://webexapis.com/v1/people/me`,
  same bearer token as the hosted MCP) once per sign-in. `sb_core/webex_tools.py`'s
  `_ensure_identity` calls it only if `sb_webex_identity` (a single-row
  cache table) is empty; the cached email is never re-fetched automatically.
- **Parent lookup**: `client.py::get_message(message_id)` hits
  `.../messages/{id}` for one message, wrapped in a
  `functools.lru_cache(maxsize=500)` keyed on `(token, message_id)` so a
  single sync's repeated parent lookups don't re-hit the network. The cache
  is process-lifetime, not persisted across processes or syncs.
- **Normalization**: `services/webex/src/sb_webex/normalize.py::messages()`
  accepts optional `me_email` and `parent_lookup` params; when a message has
  a `parentId`, it calls `parent_lookup`, and if the parent's `personEmail`
  matches `me_email`, sets `is_reply_to_me=True` and populates
  `parent_sender_email`. A failed or missing lookup never raises and never
  blocks the surrounding sync — it just leaves those fields at their
  defaults.
- **Backfill**: `sync_webex` only enriches newly-pulled messages (enriching
  the entire historical mirror on every sync would balloon it with parent
  lookups). `webex_rethread(limit=500)` is a separate, **manually-triggered**
  MCP tool that walks existing rows with a `parent_message_id` but no
  `parent_sender_email` and fills them in; it is never auto-run.

Migration `_m10_webex_threads` added the three new `sb_webex_messages`
columns (`parent_message_id`, `parent_sender_email`, `is_reply_to_me`) and
the `sb_webex_identity` table, all via idempotent `_add_column` calls plus a
`CREATE TABLE IF NOT EXISTS`.

## Goals registry

`services/core/src/sb_core/goals_tools.py` (mounted as `"sb-goals"`) is a
DB-backed goals registry (`sb_goals_registry`, migration `_m9_batch`),
intentionally separate from the pre-existing YAML-fed `goals.py` /
`get_goals` tool (`ritual_tools.py`) used by `plan_day`. Tools use a `_v2`
suffix (`list_goals_v2`, `get_goal_v2`) to avoid colliding with the older
tool name. `add_goal`/`update_goal` take `tier` (contractual/quarterly/
weekly), `title`, `description`, `keywords`, `target_date`; `archive_goal` is
a status transition (`status='archived'`), never a delete. `score_alignment`
scores one todo or ledger row against every active goal's keywords
(normalized keyword-overlap count, 0..1, no LLM). `heatmap_last_week` counts
matching ledger entries and completed todos per goal over the last 7 days.
The dashboard surfaces this at `/goals` (tier tabs, heatmap, drift alerts).

## Scheduler

`services/core/src/sb_core/scheduler.py` (mounted as `"sb-scheduler"`) is a
small, dependency-free cron engine: a hand-written 5-field parser (`*`,
single values, comma lists, ranges, step values — no external `croniter`
dependency) plus `run_due_schedules`, which finds the most recent
cron-matching minute for each enabled row in `sb_scheduled_rituals` (by
searching backward up to 8 days) and compares it against `last_run_at` to
decide whether the schedule is due. Ritual dispatch calls the existing
module-level functions directly (`ritual_tools.wrap_day`/`.standup`/
`.plan_day`, `reports.templates.daily`/`.weekly`/`.monthly`) rather than
going through another MCP round-trip. The `com.praspr.sb-scheduler` launchd
job (`StartInterval=300`) is what actually invokes `run_due_schedules` in
production — the dashboard's Settings → Schedules tab only edits rows.

## URL hints and bulk import

- `services/core/src/sb_core/url_hints.py` (`"sb-url-hints"`) — one tool,
  `parse_url_hint(url)`, a pure regex classifier (no network, no side
  effects) returning `{kind, extracted, suggested_action}` for JIRA browse
  links, `webexteams://`/`web.webex.com` links, GitHub PR links, `file://`
  URIs, and a generic fallback. Consumed by the command palette's URL smart
  handler.
- `services/core/src/sb_core/jira_bulk.py` (`"sb-jira-bulk"`) — one tool,
  `bulk_import_jira_to_todos(project=None, statuses=None, dry_run=False)`,
  which creates a todo per matching local-mirror JIRA ticket
  (idempotent via the existing `external_source='jira'`/`external_ref`
  upsert), mapping JIRA priority onto todo priority (Highest→1, High→2,
  Medium→3, Low/Lowest→4) and populating the new `jira_ref` column.

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
(`skill://<id>`), and disables ones that dropped out. A new project skill,
`harness/skills/ledger/SKILL.md`, documents cross-harness ledger capture; a
copied skill, `harness/skills/cisco-iq-performance-checkin/`, was brought in
verbatim from `ciq/.cursor/skills/` for performance-checkin workflows.

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
  already present). `propose_meeting_notes` (triage) also queues proposals
  through the same `sb_proposals` table, just with `kind='ledger_entry'` or
  `'todo'`. The dashboard's `/proposals` page lists and approves/rejects
  every pending proposal regardless of kind.
- **`standup`** — deterministic (no LLM), builds 5–8 bullets from today's
  persisted plan, whether yesterday's wrap exists, and today's open P1/P2
  todos plus any meetings for the day.

These rituals are surfaced as Today/Wrap/Standup sub-tabs on the dashboard's
`/reports` page — the standalone `/today`, `/wrap`, `/standup` routes from
earlier phases were removed.

Note (still true): `services/core/src/sb_core/plan_tools.py` implements an
earlier, functionally-overlapping version of `whoami`/`get_roots`/
`get_goals`/`plan_day`/`get_day` under a separate FastMCP instance
(`"sb-plan"`), but it is **not mounted** anywhere in `mcp_app.py` — only
`ritual_tools.mcp` is mounted. `plan_tools.py` still has a dedicated test
file (`services/core/tests/test_plan_tools.py`) but is dead code from the
running server's perspective. Treat `ritual_tools.py` as the source of truth
for these tool names.

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
- Webex is read-only for every tool **except one, explicit** write path:
  `webex_post_message` (`sb_core/webex_post.py`, mounted as
  `"sb-webex-post"`), which posts exactly the message the caller supplies to
  exactly the space they name — never invoked by any sync or scheduled job,
  only by the dashboard's "Post to Webex" report action or a direct tool
  call.
- Skill indexing is allow-listed to specific project/harness directories; it
  never walks the rest of the home directory (`skills.default_roots`).
- The narrative ledger is append-only at the database level (triggers, not
  just convention) — see "The narrative ledger" above. Content is always
  redacted before persistence rather than rejected.
- Local filesystem writes outside the SQLite databases and the JIRA markdown
  mirror are limited to: `approve_proposal`'s `CHANGELOG.md` append (gated by
  path-safety checks), and `ledger_sync.append_to_changelog`'s per-project
  `CHANGELOG.md` append (gated by the project registry + `flock`).

