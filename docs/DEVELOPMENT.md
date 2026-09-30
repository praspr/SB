# Development

## Python services

Each service uses `uv` with its own `pyproject.toml`. From a service
directory:

```bash
cd sb/services/core   # or todos, jira, webex, cli
uv sync --group dev
```

Running tests:

```bash
cd sb/services/core  && uv run pytest -q
cd sb/services/todos && uv run pytest -q
cd sb/services/jira  && uv run pytest -q
cd sb/services/webex && uv run pytest -q
cd sb/services/cli   && uv run pytest -q
```

Always invoke `uv run pytest`, never a bare `pytest` — if a service's
`pyproject.toml` doesn't declare `pytest` as a dependency (a real bug fixed
in `services/webex/pyproject.toml` during Phase 2c: it silently fell back to
a global, wrong-Python `pytest` on `PATH` that couldn't even import
`httpx`), `uv run pytest` will tell you clearly via an import error rather
than mysteriously passing against the wrong interpreter. If you hit that,
add `[dependency-groups] dev = ["pytest>=8.3"]` to that service's
`pyproject.toml` and re-run `uv sync --group dev`.

`services/core` depends on `sb-jira`, `sb-todos`, and `sb-webex` as editable
path sources (see `[tool.uv.sources]` in `services/core/pyproject.toml`), so
`uv sync` inside `services/core` pulls in the sibling packages from source.

No repo-wide lint/format tool is configured for Python in this repo; check
each service's `pyproject.toml` before assuming one exists.

## Web dashboard

```bash
cd sb/web
npm install
npm run dev       # http://localhost:5173
npm run build     # tsc -b && vite build → web/dist/
npm run lint      # tsc --noEmit
npm run test      # vitest run
```

TypeScript project references drive `tsc -b`; see `web/tsconfig*.json` for
the exact project graph. Path alias `@` resolves to `web/src` (see
`web/vite.config.ts` and the matching `tsconfig` paths).

## Repo conventions

- **CHANGELOG policy**: `CHANGELOG.md` at the repo root is the single
  changelog. New entries go under `## Unreleased` in `### Added` / `### Changed`
  / etc. sections, written densely and factually (see existing entries for
  tone). The `wrap_day` ritual can also *propose* an entry, but only
  `approve_proposal` actually appends it, and only under a configured root's
  `CHANGELOG.md`. Separately, the narrative ledger's dual-write
  (`ledger_log`/`sb log`) appends dated `## [YYYY-MM-DD]` bullets to the
  `sb` project's `CHANGELOG.md` any time an entry is logged for project
  `sb` — the two mechanisms write to the same file but through different
  code paths (`ritual_tools.approve_proposal` vs.
  `ledger_sync.append_to_changelog`); don't be surprised to see both a
  `## Unreleased` section and dated `## [...]` sections in the same file.
- **Roadmap**: `PENDING.md` is the source of truth for what is not yet
  built, ordered by effort/value. Note: as of this writing, parts of
  `PENDING.md` describe an earlier architecture (separate `sb-todos`/`sb-jira`
  REST services) that predates the unified `sb-core` MCP rollout described in
  the README and `CHANGELOG.md` — treat `PENDING.md`'s specific service/API
  references as historical context, and its ordering/priorities as current.

## launchd operations

`com.praspr.sb` is the primary sb launchd job; two supporting jobs
(`com.praspr.sb-morning-open`, `com.praspr.sb-scheduler`) ship alongside it.
Plists live in `services/core/launchd/` (see `services/core/launchd/README.md`
for the full reference).

```bash
# Install
cp services/core/launchd/com.praspr.sb.plist ~/Library/LaunchAgents/
cp services/core/launchd/com.praspr.sb-morning-open.plist ~/Library/LaunchAgents/
cp services/core/launchd/com.praspr.sb-scheduler.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb-morning-open.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb-scheduler.plist

# Restart the core process after a schema or tool code change
launchctl kickstart -k gui/$(id -u)/com.praspr.sb

# Remove
launchctl bootout gui/$(id -u)/com.praspr.sb-scheduler || true
launchctl bootout gui/$(id -u)/com.praspr.sb-morning-open || true
launchctl bootout gui/$(id -u)/com.praspr.sb || true
rm -f ~/Library/LaunchAgents/com.praspr.sb*.plist
```

Logs: `/tmp/sb.{out,err}.log` for the core process, plus
`/tmp/sb-morning-open.{out,err}.log` and `/tmp/sb-scheduler.{out,err}.log`
for the two supporting jobs. Only `com.praspr.sb` ever needs a kickstart —
the morning-open and scheduler jobs just shell out to `curl`/`open`, never
to the long-running Python process, so there's nothing in them to restart.

## Debugging

```bash
# Health
curl -s http://127.0.0.1:8787/health

# Tail logs
tail -f /tmp/sb.out.log /tmp/sb.err.log

# Inspect core SQLite
sqlite3 ~/.local/share/sb/core.db
sqlite> .tables
sqlite> SELECT * FROM sb_signals ORDER BY id DESC LIMIT 20;

# Inspect todos SQLite
sqlite3 ~/.local/share/sb/todos.db
```

`GET /health` never contacts Atlassian or Webex, so a `degraded` status
means the local SQLite connection failed — check file permissions and that
the parent directory (`~/.local/share/sb/`) exists.

### Reading the narrative ledger

```bash
sqlite3 ~/.local/share/sb/core.db \
  "SELECT ts, project, action_verb, summary FROM sb_ledger ORDER BY id DESC LIMIT 20;"

# Full-text search (avoid hyphenated terms -- see the FTS5 caveat in ARCHITECTURE.md)
sqlite3 ~/.local/share/sb/core.db \
  "SELECT l.id, l.summary FROM sb_ledger_fts f JOIN sb_ledger l ON l.id = f.rowid WHERE sb_ledger_fts MATCH 'apisix';"

# Confirm the append-only triggers are installed
sqlite3 ~/.local/share/sb/core.db \
  "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'sb_ledger';"
```

Remember: any `UPDATE`/`DELETE` against `sb_ledger` raises
`sqlite3.IntegrityError('sb_ledger is append-only')` — including from the
`sqlite3` CLI itself. That's expected; write a correcting row instead.

## Adding a new report template

`services/core/src/sb_core/reports/templates.py` holds the four report
builders (`daily`, `weekly`, `monthly`, `query`). To add a fifth:

1. Write a new function with the same shape: accept `conn` plus keyword
   filters, return `{"markdown": str, "citations": list[int], "range"?: {...}}`
   (or `{"mode": ...}` for an LLM-optional one like `query`). Reuse
   `search_ledger`/`open_threads` from `sb_core/store/ledger.py` — do not
   re-implement ledger queries.
2. Mount it as a tool in `services/core/src/sb_core/reports_tools.py`
   (`@mcp.tool()`, parse any date-shaped args defensively and return
   `{"error": "..."}` rather than raising).
3. Add it to `scheduler.py::_ritual_dispatch()` if it should be
   schedulable, and to the ritual dropdown options
   (`services/core/src/sb_core/scheduler.py`'s `add_scheduled_ritual`
   validation + `web/src/components/layout/SchedulesTab.tsx`'s
   `RITUAL_OPTIONS`) if so.
4. Add template tests under `services/core/tests/test_reports_templates.py`
   and tool tests under `test_reports_tools.py`.
5. If the web app should run it, add a template option to
   `web/src/pages/ReportsPage.tsx`'s template list and a wrapper in
   `web/src/lib/reports.ts`.

## Skills authoring

A skill is a directory containing a `SKILL.md` with YAML frontmatter
(`name`, `description`) followed by `---` and a markdown procedure body. An
optional `## Allowed tools` section lists tool names as `- \`tool_name\``
bullets; `sync_skills` extracts these into `allowed_tools`.

For a skill to be indexed, its parent directory must be one of the
allow-listed roots (see `docs/ARCHITECTURE.md` → Skills indexing):

- `<repo>/harness/skills/<skill-id>/SKILL.md`
- `<repo>/.cursor/skills/<skill-id>/SKILL.md`
- `~/.cursor/skills/<skill-id>/SKILL.md`
- `~/.claude/skills/<skill-id>/SKILL.md`
- any directory listed in `SB_CORE_EXTRA_SKILL_ROOTS`

The `<skill-id>` directory name must match `^[a-z0-9][a-z0-9_-]{0,64}$`.
Project skills live under `harness/skills/` — run `ls harness/skills/` for
the current list (names only; see each `SKILL.md` for content). Two notable
additions since the original doc pass: `ledger/SKILL.md` (Phase 1b — how to
capture cross-harness activity into the narrative ledger) and
`cisco-iq-performance-checkin/` (Phase 2a — copied verbatim from
`ciq/.cursor/skills/cisco-iq-performance-checkin/`, no modifications).

After adding or editing a `SKILL.md`, call the `sync_skills` MCP tool (or
restart sb-core) to re-index; the dashboard's `/skills` page reflects the
result.
