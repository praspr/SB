# Services

One section per service. All Python services are libraries mounted
in-process by `sb-core`; only `sb-core` runs its own HTTP server.

## sb-core

- **Purpose**: Unified local MCP host. Owns the `/mcp` and `/sse` transports,
  `/health`, and the Webex OAuth redirect endpoints. Mounts every other
  service's MCP tools in-process and implements the chief-of-staff rituals
  (plan/wrap/standup/proposals), signal ledger, skill indexing, and read-only
  chat.
- **Storage**: `~/.local/share/sb/core.db` (SQLite, WAL, foreign keys on,
  5-second busy timeout, versioned migrations — `services/core/src/sb_core/store/db.py`).
- **Entry point**: `services/core/src/sb_core/main.py` (`app` — FastAPI ASGI
  app), built on the FastMCP instance in `services/core/src/sb_core/mcp_app.py`.
- **MCP tools it contributes directly**:
  - `system_status` — privacy-safe readiness summary (also backs `/health`)
  - `sync_skills`, `list_skills`, `get_skill` — skill indexing (`skills.py`)
  - `ask_sb` — read-only cited chat over local todos/JIRA/signals (`chat_tools.py`)
  - `sync_adapters`, `sync_status`, `search_signals` — signal ledger (`sync_tools.py`)
  - `whoami`, `get_roots`, `get_goals`, `plan_day`, `get_day`, `standup`,
    `wrap_day`, `list_proposals`, `reject_proposal`, `approve_proposal` —
    daily rituals (`ritual_tools.py`)
  - `webex_status`, `webex_login_url`, `sync_webex`, `list_webex_meetings`,
    `list_webex_spaces`, `list_webex_messages`, `webex_attention`,
    `summarize_webex_space` — Webex mirror (`webex_tools.py`)
- **Notable modules**: `config.py` (env/YAML settings), `goals.py`
  (contractual/quarterly/weekly goals file), `ranker.py` (deterministic todo
  ranking), `llm.py` (claudegate client with citation-validated fallback),
  `webex_store.py` (Webex mirror tables), `adapters/` (todos, jira,
  changelog, git signal adapters), `store/` (db, daily, signals, models).
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
  - `todo_add` — create a todo; idempotent upsert on `external_source` + `external_ref`
  - `todo_complete` / `todo_uncomplete` — mark/unmark complete
  - `todo_update` — update any field
  - `todo_delete` — delete a todo
  - `todo_search` — substring search on title + description
- **Notable modules**: `config.py`, `models.py` (`TodoCreate`/`TodoUpdate`),
  `db.py`, `migrations/001_init.sql`, `handlers.py` (CRUD + idempotent
  upsert via `idx_todos_ext`).
- **Tests**: `services/todos/tests/` — `test_db.py`, `test_handlers.py`,
  `test_mcp.py`.
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

  Note: the top-level README lists only four JIRA tools
  (`list_jira_tickets`, `get_jira_ticket`, `sync_jira`, `jira_status`).
  `track_jira` and `untrack_jira` exist in source and are documented in
  CHANGELOG.md ("Add Track JIRA on the JIRA page") but are missing from the
  README's tool table — treat this documentation set as the corrected list.
- **Notable modules**: `atlassian_client.py` (search/fetch via enhanced
  `/rest/api/3/search/jql`, token pagination), `file_store.py` (load/filter
  the markdown mirror), `sync.py`, `tracking.py` (tracked-key persistence),
  `format.py`, `history.py` (`tickethistory.md` regeneration).
- **Auth**: Atlassian API token from macOS Keychain (`keyring`, service `sb`,
  account `jira.token`) or `ATLASSIAN_API_TOKEN` env var. Never written to
  the repo.
- **Tests**: `services/jira/tests/`.
- Full README: `services/jira/README.md`.

## sb-webex

- **Purpose**: Read-only client library for a hosted Webex MCP server. Mounts
  Webex tools in-process on `sb-core`; the actual Webex data source is
  external (`https://aicoding-mcp-webexapis.cisco.com/mcp/`), not a local
  process.
- **Storage**: no local database of its own — the mirror tables
  (`sb_webex_meetings`, `sb_webex_spaces`, `sb_webex_messages`) live in
  `sb-core`'s `core.db`, written by `sb_core/webex_store.py`.
- **Entry point**: `services/webex/src/sb_webex/client.py` (`McpClient`,
  `begin_login`, `finish_login`, `access_token`, `authenticated`) — consumed
  by `services/core/src/sb_core/webex_tools.py`, which defines the actual
  MCP tools mounted as `"sb-webex"`.
- **MCP tools contributed via `sb_core/webex_tools.py`**:
  - `webex_status` — sign-in presence + mirrored counts (never returns tokens)
  - `webex_login_url` — OAuth URL for one-time sign-in
  - `sync_webex` — pull meetings/spaces/message previews into the local mirror
  - `list_webex_meetings`, `list_webex_spaces`, `list_webex_messages` — read the mirror
  - `webex_attention` — rank mentions/DMs/questions needing attention
  - `summarize_webex_space` — LLM summary of one space, citation-gated (falls back deterministically)
- **Auth**: public PKCE OAuth; sign in once via `GET /webex/login` on
  sb-core. Tokens stored in macOS Keychain, service `sb`. Python trusts the
  Cisco certificate chain via `truststore` (OS store).
- **Notable modules**: `normalize.py` (`meetings`, `spaces`, `messages`,
  `attention`, `readable_tools` — normalizes hosted-MCP tool payloads).
- **Tests**: `services/webex/tests/` (see `pyproject.toml` `testpaths`).
- No standalone README; see `services/webex/pyproject.toml`.
