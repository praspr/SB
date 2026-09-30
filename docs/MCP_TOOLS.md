# MCP Tools Reference

All tools below are exposed by one MCP server named **`sb`** at
**`http://127.0.0.1:8787/mcp`** (Streamable HTTP; SSE at `/sse`). There are
no separate network servers per domain — everything is mounted in-process
onto the single FastMCP instance in `services/core/src/sb_core/mcp_app.py`.

As of schema version 10, `GET /health` reports **76 tools / 20 prompts / 20
resources** (prompts/resources come from indexed skills, not listed here —
see `docs/ARCHITECTURE.md` → Skills indexing).

Classification: **write** = mutates a local store or file; **read** = no
mutation.

## sb-todos (8 tools + `expand_recurring_todo`)

Source: `services/todos/src/sb_todos/mcp_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `todo_list` | read | List todos, optionally filtered | `status="open"`, `priority`, `domain`, `tag`, `limit=100` |
| `todo_get` | read | Fetch one todo by id | `todo_id` |
| `todo_add` | write | Create a todo; idempotent upsert on `external_source`+`external_ref` | `title`, `description`, `priority=4`, `due_date`, `due_time`, `tags`, `domain="work"`, `external_source`, `external_ref`, `goal_id`, `jira_ref`, `recurrence_rule`, `parent_todo_id` |
| `todo_complete` | write | Mark complete; auto-materializes the next recurring instance if `recurrence_rule` is set | `todo_id` |
| `todo_uncomplete` | write | Un-mark complete | `todo_id` |
| `todo_update` | write | Update any provided field | `todo_id`, `title`, `description`, `priority`, `due_date`, `due_time`, `tags`, `domain`, `goal_id`, `jira_ref`, `recurrence_rule`, `parent_todo_id` |
| `todo_delete` | write | Delete a todo | `todo_id` |
| `todo_search` | read | Substring search over title + description | `query`, `limit=20` |
| `expand_recurring_todo` | write | Manually materialize the next instance of a recurring todo; idempotent on `(parent_todo_id, due_date)` | `todo_id` |

`recurrence_rule` is RRULE-lite: `FREQ=DAILY`, `FREQ=WEEKLY;BYDAY=MO,WE`,
`FREQ=MONTHLY;BYMONTHDAY=1` (clamped to the last valid day of a shorter
month). `goal_id` points at `sb_goals_registry` (see sb-goals below).

## sb-jira (6 tools, pull-only)

Source: `services/jira/src/sb_jira/mcp_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `list_jira_tickets` | read | List tickets from the local mirror | `status`, `priority`, `project`, `projects`, `q`, `hide_closed=False`, `limit=100` |
| `get_jira_ticket` | read | One ticket by key, full detail with sections | `key` |
| `track_jira` | write (local file) | Fetch one ticket by key/browse link, keep tracked across syncs | `issue` |
| `untrack_jira` | write (local state) | Stop refreshing a tracked ticket; file is kept | `key` |
| `sync_jira` | write (local files) | Pull from Atlassian → rewrite local markdown only; never writes upstream | — |
| `jira_status` | read | Ticket count, last local sync, Atlassian reachability probe | — |

## sb-core rituals (10 tools, `"sb-ritual"`)

Source: `services/core/src/sb_core/ritual_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `whoami` | read | Configured identity (name/email); never returns secrets | — |
| `get_roots` | read | Configured project roots, with labels/domain when supplied | — |
| `get_goals` | read | YAML-fed goals grouped contractual/quarterly/weekly (distinct from the DB-backed sb-goals below) | `active_only=True` |
| `plan_day` | write (persists plan) | Rank open todos into a persisted daily plan; never overwrites wrap | `date`, `refresh=False` |
| `get_day` | read | Persisted plan/wrap for a date | `date` |
| `standup` | read | 5–8 deterministic bullets from today's plan, yesterday's wrap, open P1/P2 todos, meetings | `date` |
| `wrap_day` | write when `dry_run=False` | Evidence-backed day wrap; citation-gated LLM narrative with deterministic fallback; queues a CHANGELOG proposal | `date`, `dry_run=True`, `refresh=False` |
| `list_proposals` | read | List proposals by status | `status="pending"` |
| `reject_proposal` | write (status only) | Mark a proposal rejected | `proposal_id` |
| `approve_proposal` | write (appends `CHANGELOG.md`) | Execute a pending `changelog` proposal after strict path safety | `proposal_id` |

Note: `services/core/src/sb_core/plan_tools.py` implements an overlapping,
**unmounted** `"sb-plan"` FastMCP instance with the same tool names — dead
code from the running server's perspective (see `docs/ARCHITECTURE.md`).
`ritual_tools.py` is the source of truth.

## sb-core skills (3 tools)

Source: `services/core/src/sb_core/skills.py`, registered via
`register_skill_tools(mcp)` in `mcp_app.py` (not the `@mcp.tool()` decorator
pattern, but the same effect).

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `sync_skills` | write (index) | Rescan allow-listed `SKILL.md` roots | — |
| `list_skills` | read | List indexed skills | `source`, `status`, `query` |
| `get_skill` | read | One skill's metadata + bounded procedure markdown | `skill_id` |

## sb-core signals (`"sb-sync"`, 3 tools)

Source: `services/core/src/sb_core/sync_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `sync_adapters` | write (signals) | Run signal adapters (`todos`, `jira`, `changelog`, `git`), per-adapter isolated with a bounded timeout | `adapters`, `since_days=30` |
| `sync_status` | read | Last sync state per adapter | — |
| `search_signals` | read | Search `sb_signals`; results are citation-ready (`id` → `[signal:N]`) | `q`, `source`, `kind`, `since`, `limit=100` |

`sync_tools._ALL_ADAPTERS` also lists `"webex"`, but no corresponding
adapter module exists — harmless, see `docs/ARCHITECTURE.md`.

## sb-ledger (9 tools, new in Phase 0)

Source: `services/core/src/sb_core/ledger_tools.py`. Backs the append-only
narrative ledger (`sb_ledger`) — see `docs/ARCHITECTURE.md` for the
append-only guarantee, redaction, session model, and dual-write protocol.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `ledger_log` | write (append-only) | Record one narrative entry; redacts, resolves/reuses a session, dual-writes to the project's `CHANGELOG.md` if registered `sync_mode='dual'` | `summary`, `project`, `action_verb="Note"`, `body`, `scope`, `refs`, `session_id`, `agent`, `working_dir`, `source_harness="mcp"` |
| `ledger_batch_log` | write (append-only) | Record multiple entries in one call; one failure never blocks the rest | `entries: list[dict]` (same fields as `ledger_log`) |
| `ledger_search` | read | Full-text (`q`) + structured (`project`/`since`/`until`/`verb`/`session_id`) search | `q`, `project`, `since`, `until`, `verb`, `session_id`, `limit=100` |
| `ledger_context` | read | Recent entries + open threads + tracked refs for a project (default window: last 48h) | `project`, `since`, `limit=30` |
| `ledger_by_ref` | read | Rows whose `refs` include a `{kind, value}` pair | `kind`, `value`, `limit=50` |
| `ledger_open_threads` | read | Entries from the last 30 days referencing a still-open JIRA ticket or todo | `project` |
| `ledger_projects` | read | List every enrolled project in the registry | — |
| `ledger_register_project` | write (registry only) | Enroll or update a project; `changelog_path` defaults to `<root>/CHANGELOG.md` | `project`, `root_path`, `changelog_path`, `sync_mode="dual"` |
| `sync_ledger_from_files` | write (hydrates `sb_ledger` only, never files) | Backfill the ledger from bullets already present in every enrolled project's `CHANGELOG.md` | — |

Citations from ledger-backed tools use `[ledger:<id>]`.

## sb-reports (4 tools, new in Phase 1a)

Source: `services/core/src/sb_core/reports_tools.py`. All four wrap
`services/core/src/sb_core/reports/templates.py` and are deterministic by
default.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `report_daily` | read | Report FOR `date` (default today): yesterday's ledger activity by project/scope, today's meetings, top open todos, open threads | `date`, `project` |
| `report_weekly` | read | 7-day rolling window ending on `week_end` (default today, inclusive); verb frequency, top references, daily digest, open threads | `week_end`, `project` |
| `report_monthly` | read | Rollup of `month` (`YYYY-MM`, default current) with sub-headings per calendar week | `month`, `project` |
| `report_query` | read | Ad-hoc "what did I do about X"; LLM-narrates with `[ledger:N]` citations when available, always falls back to a citation-only list | `q`, `project`, `since`, `until` |

Date args parse as `YYYY-MM-DD` / month as `YYYY-MM`; a malformed value
returns `{"error": "..."}` rather than raising.

## sb-triage (4 tools, new in Phase 1.5, extended in 2c)

Source: `services/core/src/sb_core/triage_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `webex_attention_ranked` | read | Ranked attention items (mention / dm / reply-to-me only — everything else is dropped) with staleness + suggested verb | `limit=30` |
| `webex_attention_filtered` | read | Same ranking, with messages from muted spaces excluded | `limit=30` |
| `pre_meeting_context` | read | Best-effort recent messages/ledger entries/related JIRAs/open todos for a meeting | `meeting_id` |
| `propose_meeting_notes` | write (queues proposals) | Draft ledger-entry and todo proposals from a recent meeting's messages; LLM with deterministic single-entry fallback | `meeting_id` |

`_triage_kind` classifies each message into exactly one of `"mention"`,
`"dm"`, or `"reply-to-me"`; anything else is dropped (no catch-all bucket).

## sb-goals (7 tools, new in Phase 2a)

Source: `services/core/src/sb_core/goals_tools.py`. DB-backed
(`sb_goals_registry`), distinct from the YAML-fed `get_goals` ritual tool
above — uses a `_v2` suffix to avoid colliding with it.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `list_goals_v2` | read | List goals, filter by tier/status | `tier`, `status="active"` |
| `get_goal_v2` | read | One goal by id | `id` |
| `add_goal` | write | Add a goal | `tier` (contractual/quarterly/weekly), `title`, `description`, `keywords`, `target_date` |
| `update_goal` | write | Update provided fields only | `id`, `title`, `description`, `keywords`, `target_date`, `tier`, `status` |
| `archive_goal` | write (status transition, never delete) | Set `status='archived'` | `id` |
| `score_alignment` | read | Score one todo or ledger row against every active goal's keywords (0..1, no LLM) | exactly one of `todo_id` / `ledger_id` |
| `heatmap_last_week` | read | Per-active-goal count of matching ledger entries + completed todos over the last 7 days, plus top refs | — |

## sb-scheduler (4 tools, new in Phase 2a)

Source: `services/core/src/sb_core/scheduler.py`. Cron parsing is a small
hand-written 5-field evaluator (no `croniter` dependency) — supports `*`,
single values, comma lists, ranges, and step values.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `add_scheduled_ritual` | write | Register a schedule; validates the ritual name and cron string eagerly | `name`, `ritual` (one of `wrap_day`/`standup`/`plan_day`/`report_daily`/`report_weekly`/`report_monthly`), `cron` (5-field, local time), `args`, `enabled=True`, `target_dir` |
| `list_scheduled_rituals` | read | List every schedule (enabled and disabled) | — |
| `delete_scheduled_ritual` | write (metadata only) | Delete a schedule — allowed, since schedules are metadata, not the ledger | `id` |
| `run_due_schedules` | write (runs due rituals) | Evaluate every enabled schedule's cron against now; run and record `last_run_at`/`last_status` for any that are due; safe to call repeatedly | — |

The `com.praspr.sb-scheduler` launchd job POSTs `run_due_schedules` every 5
minutes in production; the dashboard's Settings → Schedules tab only edits
rows.

## sb-url-hints (1 tool, new in Phase 2a)

Source: `services/core/src/sb_core/url_hints.py`. Pure regex classifier, no
network calls, no side effects.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `parse_url_hint` | read | Classify a pasted URL into `{kind, extracted, suggested_action}` — `jira` (browse link → `track_jira`), `webex` (`webexteams://` or `web.webex.com` → `open_space`), `github` (PR link → `attach_as_ref`), `file` (`file://` → `attach_as_ref`), or `generic` | `url` |

## sb-jira-bulk (1 tool, new in Phase 2a)

Source: `services/core/src/sb_core/jira_bulk.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `bulk_import_jira_to_todos` | write (todos only; read-only against Atlassian) | Create a todo per matching local-mirror JIRA ticket; idempotent via `external_source='jira'`+`external_ref`; maps JIRA priority (Highest→1, High→2, Medium→3, Low/Lowest→4) onto todo priority and populates `jira_ref` | `project`, `statuses`, `dry_run=False` |

## sb-webex-mute (3 tools, new in Phase 2a)

Source: `services/core/src/sb_core/webex_mute.py`. Local-only state; never
calls Webex, never affects what `sync_webex` pulls.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `mute_space` | write (local mirror only) | Mute one space | `space_id` |
| `unmute_space` | write (local mirror only) | Unmute one space | `space_id` |
| `list_muted_spaces` | read | List currently-muted spaces | — |

## sb-webex-post (1 tool, new in Phase 2b — the one write path)

Source: `services/core/src/sb_core/webex_post.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `webex_post_message` | write (Webex) | Post exactly the supplied message to exactly the named space via the hosted MCP's `post_webex_message` tool; never invoked by any sync or scheduled job | `space_id`, `markdown`, `message_type="text"` |

## sb-webex (9 tools)

Source: `services/core/src/sb_core/webex_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `webex_status` | read | Sign-in presence + mirrored counts (never returns tokens) | — |
| `webex_login_url` | read | OAuth URL for one-time sign-in | — |
| `sync_webex` | write (local mirror) | Pull meetings/spaces/message previews, replace local mirror; on first call after sign-in, also captures + caches identity (email/display name) for reply-to-me detection | — |
| `webex_rethread` | write (local mirror only; read-only against Webex) | Manual backfill: fill `parent_sender_email`/`is_reply_to_me` for mirrored messages that have a `parent_message_id` but were never enriched; never auto-run | `limit=500` |
| `list_webex_meetings` | read | List mirrored meetings | — |
| `list_webex_spaces` | read | List mirrored spaces | — |
| `list_webex_messages` | read | List mirrored message previews | `space_id` |
| `webex_attention` | read | Legacy unranked rank of mentions/DMs/questions (superseded by `webex_attention_ranked`/`_filtered` in sb-triage for the dashboard, but still mounted) | `limit=20` |
| `summarize_webex_space` | read | Citation-gated LLM summary of one space, falls back deterministically | `space_id` |

## sb-chat (1 tool)

Source: `services/core/src/sb_core/chat_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `ask_sb` | read | Read-only cited chat over bounded local todos/JIRA/signals/**ledger** (extended Phase 1a); never writes anything | `question` |

## sb-core meta (1 tool)

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `system_status` | read | Privacy-safe readiness summary (also backs `GET /health`) | — |

## Citation formats

| Source | Format | Used by |
|---|---|---|
| Signals | `[signal:<id>]` | `search_signals`, plans, wraps, standups, `ask_sb` |
| Ledger | `[ledger:<id>]` | `ledger_search`/`ledger_context`, all four `sb-reports` tools, `ask_sb` |
| Webex | `[webex:<id>]` | `summarize_webex_space`, `ask_sb` |
| Todos | `[todo:<id>]` | `ask_sb` |
| JIRA | `[JIRA:<KEY>]` | `ask_sb` |

## Tool count by submount (76 total)

| Submount | Tools | Phase introduced |
|---|---|---|
| sb-todos | 9 | 0 (8) → 2a (+1 `expand_recurring_todo`) |
| sb-jira | 6 | 0 (4) → 2a (+2 `track_jira`/`untrack_jira`, actually shipped alongside JIRA tracking work) |
| sb-ritual | 10 | 0 |
| skills (unnamed submount) | 3 | 0 |
| sb-sync | 3 | 0 |
| sb-ledger | 9 | 0 |
| sb-reports | 4 | 1a |
| sb-triage | 4 | 1.5 |
| sb-goals | 7 | 2a |
| sb-scheduler | 4 | 2a |
| sb-url-hints | 1 | 2a |
| sb-jira-bulk | 1 | 2a |
| sb-webex-mute | 3 | 2a |
| sb-webex-post | 1 | 2b |
| sb-webex | 9 | 0, extended 2c (`webex_rethread`) |
| sb-chat | 1 | 0, extended 1a (ledger citations) |
| sb-core meta | 1 | 0 |
| **Total** | **76** | |
