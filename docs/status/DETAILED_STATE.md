# sb — Detailed State

## Git commits (5 total)

```
8e68992  test: Phase 1 E2E tests + privacy fix — 55 tests, 0 failures [sb]
bd4758e  feat: Phase 1 — MCP service, JIRA/tasks adapters, goals, ranker, plan/wrap, install [sb]
acaa388  test: Phase 0 pytest suite — 42 tests, 0 failures [sb]
a2a40f0  feat: Phase 0 implementation — config, models, store, adapters, cli [sb]
ab42fda  chore: Phase 0 scaffold — dirs, config, docs, migration SQL, harness stubs [sb]
```

---

## Python source file inventory

| File | Lines | Purpose |
|------|-------|---------|
| `src/sb/cli.py` | 1053 | Typer CLI — all commands (doctor·sync·signals·plan·wrap·standup·review·install·mcp·secret·config) |
| `src/sb/mcp/server.py` | 831 | FastMCP SSE server on `:8787` — 15 tools |
| `src/sb/store/repo.py` | 812 | insert_signal · get_signals · upsert_daily · proposals · sync_state |
| `src/sb/brain/llm.py` | 688 | claudegate `:9999` client — 3 tiers, SHA-256 cache, cost log |
| `src/sb/adapters/jira.py` | 550 | Atlassian REST v3, ADF→text, token from Keychain, task upsert |
| `src/sb/adapters/changelog.py` | 486 | `## [YYYY-MM-DD]` parser + walker |
| `src/sb/brain/wrap.py` | 478 | Evidence harvest → LLM draft → gap questions → CHANGELOG proposals |
| `src/sb/brain/rank.py` | 453 | Pure RICE+Eisenhower ranker (WLB + domain weights) |
| `src/sb/adapters/git.py` | 453 | `git log` walker, conventional commit + JIRA extraction |
| `src/sb/models.py` | 410 | Signal, Task, Proposal, DailyEntry, Health, SyncState |
| `src/sb/config.py` | 341 | Layered pydantic-settings config |
| `src/sb/adapters/tasks_local.py` | 317 | Manual tasks ↔ signal stream |
| `src/sb/brain/plan.py` | 306 | Morning brief synthesis |
| `src/sb/store/db.py` | 260 | Connection, migration runner (900-series, additive-only) |
| `src/sb/adapters/base.py` | 248 | Adapter protocol, registry, isolated `run_adapter` |
| `src/sb/goals.py` | 238 | YAML goals loader, keyword alignment scoring |
| `src/sb/secrets.py` | 199 | Keyring wrapper — refuses file-based tokens |

**Total production code:** ~8,323 lines across 17 modules.

---

## Test coverage (55 tests, all passing)

| File | Tests | What's covered |
|------|-------|----------------|
| `tests/test_migration.py` | 7 | Coexistence gate (todoist schema untouched, sb v900, idempotent) |
| `tests/test_repo.py` | 13 | Signal/proposal/daily/sync-state round-trips |
| `tests/test_changelog_adapter.py` | 11 | Parser (edge cases, JIRA refs, since filter, same-day headings) |
| `tests/test_config.py` | 7 | Layered config (defaults, overrides, path expansion, singleton) |
| `tests/test_privacy.py` | 3 | No secrets/personal paths in tracked files |
| `tests/test_e2e.py` | 6 | User journeys (planning, idempotent sync, wrap evidence, MCP tools, install) |
| `tests/test_e2e_ranker.py` | 8 | Ranker properties (P1>P4, overdue boost, domain weights, sort order, bounds) |

Run: `.venv/bin/pytest tests/ -q`

---

## Live services (as of snapshot)

| Service | Status | Detail |
|---------|--------|--------|
| MCP server | ✅ Running | PID 84762, `127.0.0.1:8787`, SSE transport |
| launchd daemon | ✅ Loaded | `com.praspr.sb`, KeepAlive=true, RestartThrottle=10s |
| claudegate | ✅ Reachable | `:9999`, GitHub Copilot backend |
| TodoLocal DB | ✅ Migrated | `sb_migrations` at version 900, todoist versions [1,2] intact |

---

## Harness wiring

All 5 harnesses configured by `sb install --all`:

| Harness | MCP config file | Type |
|---------|-----------------|------|
| Claude Code | `~/.claude.json` → `mcpServers.sb` | `http` |
| OpenCode | `~/.config/opencode/opencode.json` → `mcp.sb` | `remote` |
| Cursor | `~/.cursor/mcp.json` → `mcpServers.sb` + `rules/sb.mdc` | `sse` |
| VS Code | `code_home/.vscode/mcp.json` → `servers.sb` | `sse` |
| launchd | `~/Library/LaunchAgents/com.praspr.sb.plist` | daemon |

Symlinks created:

- `~/.claude/skills/sb` → `harness/skills/sb`
- `~/.config/opencode/skills/sb` → `harness/skills/sb`
- `~/.cursor/skills/sb` → `harness/skills/sb`
- `~/.claude/commands/{plan-day,wrap-day,standup,sb-ask}.md`
- `~/.config/opencode/command/{plan-day,wrap-day,standup,sb-ask}.md`
- `~/.claude/agents/sb.md`
- `~/.config/opencode/agents/sb.md`

---

## Migration status

`~/Library/Application Support/TodoLocal/todo.db`:

| Table origin | Versions | Added by |
|--------------|----------|----------|
| `schema_migrations` | `[1, 2]` | todoist-local (untouched) |
| `sb_migrations` | `[900]` | sb (additive-only) |

sb-added columns on `tasks`:
`sb_source`, `sb_ref`, `sb_url`, `sb_domain`, `sb_root`, `sb_due_time`, `sb_energy`, `sb_score`, `sb_rationale`

sb-added tables: `sb_signals`, `sb_daily`, `sb_proposals`, `sb_sync_state`, `sb_migrations`

---

## Configuration files

| Path | Purpose |
|------|---------|
| `~/.config/sb/config.yaml` | User config (identity, roots, LLM tier map, domain policies) |
| `~/.config/sb/goals.yaml` | Tiered goals (contractual/quarterly/weekly) with keywords |
| `~/.local/share/sb/cache/` | LLM content-hash cache |
| `~/.local/share/sb/llm.jsonl` | Cost log (per-call tokens) |
| `~/.local/share/sb/service.log` | launchd service stdout/stderr |
| macOS Keychain (`sb` service) | Secrets (JIRA token, etc.) |

---

## MCP tool surface (15 tools)

Reachable at `http://127.0.0.1:8787/sse` from any MCP-capable harness.

**State** — `list_tasks`, `get_task`, `create_task`, `complete_task`
**Rituals** — `plan_day`, `wrap_day`, `standup`
**Evidence** — `search_signals`, `get_day`
**Sync** — `sync_adapters`, `sync_status`
**Proposals** — `list_proposals`, `approve_proposal`, `reject_proposal`
**Context** — `get_goals`, `get_roots`, `whoami`

---

## Registered adapters (4)

Verified by `sb.adapters.base.list_adapters()`:

| Adapter | Probe | Signals emitted |
|---------|-------|-----------------|
| `changelog` | ✅ ok | 64 (from `ciq` root, last 30d) |
| `git` | ✅ ok | 4 (matching user's git_authors) |
| `jira` | ⚠️ unavailable | 0 (no token set yet) |
| `tasks` | ✅ ok | 0 (no manual tasks in DB) |
