# Services

One section per service. All Python services except `sb-cli` are libraries
mounted in-process by `sb-core`; only `sb-core` runs its own HTTP server.
`sb-cli` is a separate, stateless command-line client.

## sb-core

- **Purpose**: Unified local MCP host. Owns the `/mcp` and `/sse` transports,
  `/health`, and the Webex OAuth redirect endpoints. Mounts every other
  service's MCP tools in-process and implements the chief-of-staff rituals
  (plan/wrap/standup/proposals), the append-only narrative ledger, reports,
  comms triage, a DB-backed goals registry, a cron-lite scheduler, signal
  adapters, skill indexing, URL classification, bulk JIRA import, and
  read-only chat.
- **Storage**: `~/.local/share/sb/core.db` (SQLite, WAL, foreign keys on,
  5-second busy timeout, versioned migrations, currently schema version 10 —
  `services/core/src/sb_core/store/db.py`).
- **Entry point**: `services/core/src/sb_core/main.py` (`app` — FastAPI ASGI
  app), built on the FastMCP instance in `services/core/src/sb_core/mcp_app.py`.
- **MCP tools it contributes directly, by module** (76 tools total across
  all mounted submounts; see `docs/MCP_TOOLS.md` for the full per-tool
  reference):
  - `skills.py` — `sync_skills`, `list_skills`, `get_skill` (+ skill prompts/resources)
  - `chat_tools.py` — `ask_sb` (now cites `[ledger:N]` alongside signal/todo/jira/webex kinds)
  - `sync_tools.py` — `sync_adapters`, `sync_status`, `search_signals`
  - `ritual_tools.py` — `whoami`, `get_roots`, `get_goals`, `plan_day`, `get_day`,
    `standup`, `wrap_day`, `list_proposals`, `reject_proposal`, `approve_proposal`
  - `ledger_tools.py` (new, Phase 0) — `ledger_log`, `ledger_batch_log`,
    `ledger_search`, `ledger_context`, `ledger_by_ref`, `ledger_open_threads`,
    `ledger_projects`, `ledger_register_project`, `sync_ledger_from_files`
  - `reports_tools.py` (new, Phase 1a) — `report_daily`, `report_weekly`,
    `report_monthly`, `report_query`
  - `triage_tools.py` (new, Phase 1.5) — `webex_attention_ranked`,
    `webex_attention_filtered`, `pre_meeting_context`, `propose_meeting_notes`
  - `goals_tools.py` (new, Phase 2a) — `list_goals_v2`, `get_goal_v2`,
    `add_goal`, `update_goal`, `archive_goal`, `score_alignment`,
    `heatmap_last_week`
  - `scheduler.py` (new, Phase 2a) — `add_scheduled_ritual`,
    `list_scheduled_rituals`, `delete_scheduled_ritual`, `run_due_schedules`
  - `url_hints.py` (new, Phase 2a) — `parse_url_hint`
  - `jira_bulk.py` (new, Phase 2a) — `bulk_import_jira_to_todos`
  - `webex_mute.py` (new, Phase 2a) — `mute_space`, `unmute_space`,
    `list_muted_spaces`
  - `webex_post.py` (new, Phase 2b) — `webex_post_message` (the one
    write-capable Webex tool)
  - `webex_tools.py` — `webex_status`, `webex_login_url`, `sync_webex`,
    `webex_rethread` (new, Phase 2c), `list_webex_meetings`,
    `list_webex_spaces`, `list_webex_messages`, `webex_attention`,
    `summarize_webex_space`
  - `mcp_app.py` — `system_status` (also backs `/health`)
- **Notable modules**:
  - `config.py` (env/YAML settings; now includes `ledger_roots`, `llm_model`
    default `claude-haiku-4.5-low`, `seed_registry_if_empty`)
  - `goals.py` (YAML-fed contractual/quarterly/weekly goals file — distinct
    from the DB-backed `sb_goals_registry` used by `goals_tools.py`)
  - `ranker.py` (deterministic todo ranking for `plan_day`)
  - `llm.py` (claudegate client with content-addressed cache and
    citation-validated fallback)
  - `webex_store.py` (Webex mirror tables, including `sb_webex_identity` and
    the mute/muted-space helpers)
  - `adapters/` (todos, jira, changelog — now with ledger auto-promotion —
    and git signal adapters)
  - `store/` — `db.py` (migrations), `daily.py`, `signals.py`, `models.py`,
    and (new, Phase 0) `ledger.py` (append/search/context/by_ref/open_threads,
    project registry CRUD)
  - `ledger_redact.py`, `ledger_session.py`, `ledger_sync.py` (new, Phase 0 —
    see `docs/ARCHITECTURE.md` for the full ledger design)
  - `reports/templates.py` (new, Phase 1a — the four report builders)
- **Tests**: `services/core/tests/`.
- No standalone README; see `services/core/pyproject.toml` for dependencies.

## sb-todos

- **Purpose**: SQLite-backed todo storage and MCP tools. A library mounted
  in-process by `sb-core`; does not run its own HTTP server or REST surface.
- **Storage**: `~/.local/share/sb/todos.db` (SQLite, WAL, `busy_timeout=5000`,
  foreign keys on). Override with `SB_TODOS_DB_PATH`. Parent directories are
  created automatically.
- **Entry point**: `services/todos/src/sb_todos/mcp_tools.py` (`mcp` — FastMCP
  instance named `"sb-todos"`, mounted by `sb_core.mcp_app`).
- **MCP tools**:
  - `todo_list` — list todos, filter by status/priority/domain/tag
  - `todo_get` — get one todo by id
  - `todo_add` — create a todo; idempotent upsert on `external_source` + `external_ref`;
    accepts `goal_id`, `jira_ref`, `recurrence_rule`, `parent_todo_id` (new, Phase 2a)
  - `todo_complete` / `todo_uncomplete` — mark/unmark complete; `todo_complete`
    auto-materializes the next instance via `expand_recurring_todo` when the
    todo has a `recurrence_rule` (new, Phase 2a)
  - `todo_update` — update any field, including the four new columns
  - `todo_delete` — delete a todo
  - `todo_search` — substring search on title + description
  - `expand_recurring_todo` (new, Phase 2a) — manually materialize the next
    instance of a recurring todo; idempotent on `(parent_todo_id, due_date)`
- **Notable modules**: `config.py`, `models.py` (`TodoCreate`/`TodoUpdate`,
  now with `goal_id`/`jira_ref`/`recurrence_rule`/`parent_todo_id`),
  `db.py`, `migrations/001_init.sql` + `002_batch_columns.sql` (the four new
  columns, idempotent `ALTER TABLE`), `handlers.py` (CRUD, idempotent
  upsert via `idx_todos_ext`, and the RRULE-lite recurrence engine —
  `FREQ=DAILY` / `FREQ=WEEKLY;BYDAY=...` / `FREQ=MONTHLY;BYMONTHDAY=...`,
  clamped to the last valid day of a shorter month).
- **Tests**: `services/todos/tests/` — `test_db.py`, `test_handlers.py`,
  `test_mcp.py`, `test_recurrence.py`.
- Full README: `services/todos/README.md`.

## sb-jira

- **Purpose**: Pull-only local mirror of JIRA tickets as markdown, with MCP
  tools to browse and refresh it. Never writes to Atlassian.
- **Storage**: markdown files under `ciq/docs/jira/tickets/` (path
  overridable via `SB_JIRA_TICKETS_DIR` / other `SB_JIRA_*` vars — see
  `services/jira/src/sb_jira/config.py`).
- **Entry point**: `services/jira/src/sb_jira/mcp_tools.py` (`mcp` — FastMCP
  instance named `"sb-jira"`, mounted by `sb_core.mcp_app`).
- **MCP tools**:
  - `list_jira_tickets` — filter the local mirror (status, priority, project(s), `q`, `hide_closed`)
  - `get_jira_ticket` — one ticket by key, full detail with sections
  - `track_jira` — fetch one ticket by key/browse link and keep it tracked across syncs
  - `untrack_jira` — stop refreshing a tracked ticket (file is kept)
  - `sync_jira` — pull assigned/tracked tickets from Atlassian into local markdown only
  - `jira_status` — ticket count, last local sync, Atlassian reachability probe
- **Notable modules**: `atlassian_client.py` (search/fetch via enhanced
  `/rest/api/3/search/jql`, token pagination), `file_store.py` (load/filter
  the markdown mirror), `sync.py`, `tracking.py` (tracked-key persistence
  across syncs), `format.py`, `history.py` (`tickethistory.md` regeneration).
  A separate service, `sb-jira-bulk` (`services/core/src/sb_core/jira_bulk.py`),
  imports matching mirror tickets into `sb-todos` in one call.
- **Auth**: Atlassian API token from macOS Keychain (`keyring`, service `sb`,
  account `jira.token`) or `ATLASSIAN_API_TOKEN` env var. Never written to
  the repo.
- **Tests**: `services/jira/tests/`, including `test_tracking.py`.
- Full README: `services/jira/README.md`.

## sb-webex

- **Purpose**: Client library for the hosted Webex MCP server plus two
  standard-REST-API lookups. Mounts Webex tools in-process on `sb-core`
  across four submounts (`webex_tools.py`, `webex_mute.py`, `webex_post.py`,
  and the triage tools in `triage_tools.py`); the actual Webex data source is
  external (`https://aicoding-mcp-webexapis.cisco.com/mcp/` for reads,
  `https://webexapis.com/v1/...` for `get_me`/`get_message`), not a local
  process.
- **Storage**: no local database of its own — the mirror tables
  (`sb_webex_meetings`, `sb_webex_spaces` incl. `muted`, `sb_webex_messages`
  incl. `parent_message_id`/`parent_sender_email`/`is_reply_to_me`, and the
  single-row `sb_webex_identity`) live in `sb-core`'s `core.db`, written by
  `sb_core/webex_store.py`.
- **Entry point**: `services/webex/src/sb_webex/client.py` (`McpClient`,
  `begin_login`, `finish_login`, `access_token`, `authenticated`, plus
  (new, Phase 2c) `get_me()` and `get_message(message_id)`) — consumed by
  `services/core/src/sb_core/webex_tools.py`, which defines the actual MCP
  tools mounted as `"sb-webex"`.
- **MCP tools, by contributing module**:
  - `webex_tools.py` (`"sb-webex"`) — `webex_status`, `webex_login_url`,
    `sync_webex`, `webex_rethread` (new, Phase 2c — manual thread-parent
    backfill, never auto-run), `list_webex_meetings`, `list_webex_spaces`,
    `list_webex_messages`, `webex_attention`, `summarize_webex_space`
  - `webex_mute.py` (`"sb-webex-mute"`, new Phase 2a) — `mute_space`,
    `unmute_space`, `list_muted_spaces` — local-only mute state; never calls
    Webex, never affects what `sync_webex` pulls
  - `webex_post.py` (`"sb-webex-post"`, new Phase 2b) — `webex_post_message`,
    the one explicit write path (posts exactly the message/space the caller
    supplies; never auto-invoked)
  - `triage_tools.py` (`"sb-triage"`) — `webex_attention_ranked`,
    `webex_attention_filtered` (muted spaces excluded), `pre_meeting_context`,
    `propose_meeting_notes`
- **Auth**: public PKCE OAuth; sign in once via `GET /webex/login` on
  sb-core. Tokens stored in macOS Keychain, service `sb`. Python trusts the
  Cisco certificate chain via `truststore` (OS store).
- **Notable modules**: `normalize.py` (`meetings`, `spaces`, `messages` — now
  accepting optional `me_email`/`parent_lookup` to populate the three new
  thread-reply fields — `attention`, `readable_tools`).
- **Tests**: `services/webex/tests/` (`test_normalize.py`,
  `test_oauth_state.py`, `test_client_identity.py`). **Phase 2c fix**: this
  service's `pyproject.toml` never declared `pytest` as a dependency, so
  `uv run pytest` silently fell back to a global, wrong-Python `pytest` on
  `PATH` and failed to even import `httpx`. Fixed by adding
  `[dependency-groups] dev = ["pytest>=8.3"]` and regenerating
  `services/webex/uv.lock`.
- No standalone README; see `services/webex/pyproject.toml`.

## sb-cli

- **Purpose**: Command-line client for the narrative ledger. Talks to the
  same `sb-core` `/mcp` endpoint as any other harness — no server of its
  own, no local database.
- **Entry point**: `services/cli/src/sb_cli/__main__.py` (`main()`, exposed
  as the `sb` console script via `[project.scripts]` in
  `services/cli/pyproject.toml`).
- **Commands**:
  - `sb log "<summary>" --project P [--scope S] [--verb V] [--ref KIND=VALUE[:URL]] [--session ID]`
  - `sb context --project P [--since 48h] [--limit 30]`
  - `sb search "<query>" [--project P] [--since 48h] [--verb V] [--limit 50]`
  - `sb projects list`
  - `sb projects enroll --project NAME --path /abs [--changelog /abs/CHANGELOG.md] [--sync-mode dual|sqlite-only]`
  - Common flags: `--endpoint` (default `http://127.0.0.1:8787/mcp`),
    `--json`, `--quiet`.
- **Notable modules**: `client.py` (a minimal Streamable HTTP JSON-RPC
  client — initialize/tools-call, no auth, mirroring
  `sb_webex.client.McpClient`'s wire-protocol handling), `commands/`
  (`log.py`, `context.py`, `search.py`, `projects.py`), `format.py`
  (terminal pretty-printing).
- **Dependencies**: `httpx` + stdlib `argparse` only — no heavy CLI
  framework.
- **Tests**: `services/cli/tests/` — one file per command, each mocking
  `McpClient` rather than hitting a real server.
- Full README: `services/cli/README.md`.
