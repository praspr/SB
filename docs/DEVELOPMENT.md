# Development

## Python services

Each service uses `uv` with its own `pyproject.toml`. From a service
directory:

```bash
cd sb/services/core   # or todos, jira, webex
uv sync --group dev
```

Running tests (patterns vary slightly per service's README/pyproject):

```bash
# core
cd sb/services/core && uv run pytest -q

# todos
cd sb/services/todos && .venv/bin/python -m pytest -q

# jira
cd sb/services/jira && .venv/bin/python -m pytest -q

# webex
cd sb/services/webex && uv run pytest -q
```

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
  `CHANGELOG.md`.
- **Roadmap**: `PENDING.md` is the source of truth for what is not yet
  built, ordered by effort/value. Note: as of this writing, parts of
  `PENDING.md` describe an earlier architecture (separate `sb-todos`/`sb-jira`
  REST services) that predates the unified `sb-core` MCP rollout described in
  the README and `CHANGELOG.md` — treat `PENDING.md`'s specific service/API
  references as historical context, and its ordering/priorities as current.

## launchd operations

`com.praspr.sb` is the only sb launchd job; plist at
`services/core/launchd/com.praspr.sb.plist`.

```bash
# Install
cp services/core/launchd/com.praspr.sb.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb.plist

# Restart after a code change
launchctl kickstart -k gui/$(id -u)/com.praspr.sb

# Remove
launchctl bootout gui/$(id -u)/com.praspr.sb
rm -f ~/Library/LaunchAgents/com.praspr.sb.plist
```

Logs: `/tmp/sb.out.log` and `/tmp/sb.err.log`.

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
Existing project skills under `harness/skills/`: `context`, `jira`, `plan`,
`review`, `signals`, `standup`, `sync`, `todos`, `wrap` (names only — see
each `SKILL.md` for content).

After adding or editing a `SKILL.md`, call the `sync_skills` MCP tool (or
restart sb-core) to re-index; the dashboard's `/skills` page reflects the
result.
