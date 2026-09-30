# MCP Tools Reference

All tools below are exposed by one MCP server named **`sb`** at
**`http://127.0.0.1:8787/mcp`** (Streamable HTTP; SSE at `/sse`). There are
no separate `sb-todos` / `sb-jira` network servers.

Classification: **write** = mutates a local store or file; **read** = no
mutation.

## Todos (sb-todos)

Source: `services/todos/src/sb_todos/mcp_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `todo_list` | read | List todos, optionally filtered | `status="open"`, `priority`, `domain`, `tag`, `limit=100` |
| `todo_get` | read | Fetch one todo by id | `todo_id` |
| `todo_add` | write | Create a todo; idempotent upsert on `external_source`+`external_ref` | `title`, `description`, `priority=4`, `due_date`, `due_time`, `tags`, `domain="work"`, `external_source`, `external_ref` |
| `todo_complete` | write | Mark complete | `todo_id` |
| `todo_uncomplete` | write | Un-mark complete | `todo_id` |
| `todo_update` | write | Update any provided field | `todo_id`, `title`, `description`, `priority`, `due_date`, `due_time`, `tags`, `domain` |
| `todo_delete` | write | Delete a todo | `todo_id` |
| `todo_search` | read | Substring search over title + description | `query`, `limit=20` |

## JIRA (sb-jira, pull-only)

Source: `services/jira/src/sb_jira/mcp_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `list_jira_tickets` | read | List tickets from the local mirror | `status`, `priority`, `project`, `projects`, `q`, `hide_closed=False`, `limit=100` |
| `get_jira_ticket` | read | One ticket by key, full detail with sections | `key` |
| `track_jira` | write (local file) | Fetch one ticket by key/browse link, keep tracked across syncs | `issue` |
| `untrack_jira` | write (local state) | Stop refreshing a tracked ticket; file is kept | `key` |
| `sync_jira` | write (local files) | Pull from Atlassian → rewrite local markdown only; never writes upstream | — |
| `jira_status` | read | Ticket count, last local sync, Atlassian reachability probe | — |

Note: the README's tool table omits `track_jira`/`untrack_jira`; this table
reflects source (see `docs/SERVICES.md` for details).

## Webex (sb-webex, read-only)

Source: `services/core/src/sb_core/webex_tools.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `webex_status` | read | Sign-in presence + mirrored counts | — |
| `webex_login_url` | read | OAuth URL for one-time sign-in | — |
| `sync_webex` | write (local mirror) | Pull meetings/spaces/message previews, replace local mirror | — |
| `list_webex_meetings` | read | List mirrored meetings | — |
| `list_webex_spaces` | read | List mirrored spaces | — |
| `list_webex_messages` | read | List mirrored message previews | `space_id` |
| `webex_attention` | read | Rank mentions/DMs/questions needing attention | `limit=20` |
| `summarize_webex_space` | read | Citation-gated LLM summary of one space, falls back deterministically | `space_id` |

## Core rituals and utilities (sb-core)

Source: `services/core/src/sb_core/ritual_tools.py`, `sync_tools.py`,
`chat_tools.py`, `skills.py`, `mcp_app.py`.

| Tool | R/W | Description | Key args |
|---|---|---|---|
| `whoami` | read | Configured identity (name/email); never returns secrets | — |
| `get_roots` | read | Configured project roots, with labels/domain when supplied | — |
| `get_goals` | read | Goals grouped contractual/quarterly/weekly | `active_only=True` |
| `plan_day` | write (persists plan) | Rank open todos into a persisted daily plan; never overwrites wrap | `date`, `refresh=False` |
| `get_day` | read | Persisted plan/wrap for a date | `date` |
| `standup` | read | 5–8 deterministic bullets from today's plan, yesterday's wrap, open P1/P2 todos, meetings | `date` |
| `wrap_day` | write when `dry_run=False` | Evidence-backed day wrap; citation-gated LLM narrative with deterministic fallback; queues a CHANGELOG proposal | `date`, `dry_run=True`, `refresh=False` |
| `list_proposals` | read | List proposals by status | `status="pending"` |
| `reject_proposal` | write (status only) | Mark a proposal rejected | `proposal_id` |
| `approve_proposal` | write (appends `CHANGELOG.md`) | Execute a pending `changelog` proposal after strict path safety | `proposal_id` |
| `sync_adapters` | write (signals) | Run signal adapters (`todos`, `jira`, `changelog`, `git`), per-adapter isolated with a bounded timeout | `adapters`, `since_days=30` |
| `sync_status` | read | Last sync state per adapter | — |
| `search_signals` | read | Search `sb_signals`; results are citation-ready (`id` → `[signal:N]`) | `q`, `source`, `kind`, `since`, `limit=100` |
| `sync_skills` | write (index) | Rescan allow-listed `SKILL.md` roots | — |
| `list_skills` | read | List indexed skills | `source`, `status`, `query` |
| `get_skill` | read | One skill's metadata + bounded procedure markdown | `skill_id` |
| `ask_sb` | read | Read-only cited chat over bounded local todos/JIRA/signals; never writes anything | `question` |
| `system_status` | read | Privacy-safe readiness summary (also backs `GET /health`) | — |

### Signal citation format

`search_signals` and everything that consumes signals (plans, wraps,
standups, `ask_sb`) cite evidence as `[signal:N]` where `N` is the signal
row's `id`. Webex-derived citations use `[webex:<id>]` instead (see
`webex_tools.py`).

### Signal adapter names

`sync_adapters`/`sync_status` operate over: `todos`, `jira`, `changelog`,
`git`. (`sync_tools._ALL_ADAPTERS` also lists `webex`, but no corresponding
adapter module exists under `sb_core/adapters/` — see `docs/ARCHITECTURE.md`.)
