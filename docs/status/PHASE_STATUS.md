# sb — Phase Status Brief

## What we built

`sb` — a local second-brain chief-of-staff assistant at
`~/Documents/code_home/sb/`.

It watches the exhaust of the work day (changelogs, git commits, JIRA
tickets, local tasks), maintains one canonical task store shared with the
existing `todoist-local` GUI, and bookends the day with an evidence-backed
plan and wrap.

---

## Phase 0 ✅ Done

The evidence-harvesting foundation:

- Config, models, SQLite store (additive-only, coexists safely with `todoist-local` GUI)
- `changelog.py` + `git.py` adapters — scan `code_home/{ciq, learn}` roots
- `brain/llm.py` — claudegate `:9999` (Copilot proxy) as the LLM backend
- `sb doctor`, `sb sync`, `sb signals`, `sb wrap --dry-run` CLI commands

**Acceptance gate passed:** `sb wrap --dry-run 2026-08-24` produced a
real LLM-drafted "what I did today" with `[signal:N]` citations backed by
actual changelog entries and git commits.

## Phase 1 ✅ Done

The intelligence + connectivity layer:

- `goals.yaml` + `brain/rank.py` — keyword-based goal alignment, RICE+Eisenhower scoring with WLB + domain-weight penalties
- `brain/plan.py` + `brain/wrap.py` — morning brief and end-of-day synthesis
- `adapters/jira.py` — Atlassian REST v3 (degrades gracefully without token)
- `adapters/tasks_local.py` — manual tasks from `todoist-local` GUI enter the signal stream
- `mcp/server.py` — FastMCP SSE server on `:8787`, 15 tools, running as launchd daemon
- `sb install --all` wired **5 harnesses**: Claude Code, OpenCode, Cursor, VS Code, launchd

**55/55 tests green.** MCP service live (PID 84762 on port 8787 at snapshot time).

---

## What works today

```bash
sb doctor          # 8/8 green (jira shows unavailable until token added)
sb sync            # 68+ signals from changelogs + git
sb plan            # ranked morning brief
sb wrap --dry-run  # evidence draft
sb review          # approve queued CHANGELOG proposals
```

In any harness (Claude Code, OpenCode, Cursor), the `sb` MCP tools are
available: `plan_day()`, `wrap_day()`, `search_signals()`, `list_tasks()`,
`list_proposals()`, `sync_adapters()`, `get_goals()`, `whoami()`, etc.

---

## One missing piece

**JIRA token not set.** To pull your 43 assigned tickets into the task
store and let the ranker include them:

```bash
sb secret set jira.token   # paste Atlassian API token
sb sync --adapter jira
sb plan                    # first ranked morning brief with real work
```

---

## Phase 2 queue (not started)

| Item | What it adds |
|------|-------------|
| Outlook JXA adapter | Calendar events → meeting-aware time blocks in `sb plan` |
| Webex REST adapter | DM mentions → signals → "unanswered ask" detection |
| launchd scheduler | Auto-nudge at 08:30, wrap reminder at 17:30, macOS notifications |
| `sb dash` | localhost HTML day view |
| `sb init` wizard | 10-min onboarding for teammates |
