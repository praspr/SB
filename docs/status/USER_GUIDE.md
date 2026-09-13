# sb — User Guide

## Daily commands

```bash
sb doctor                       # health check (adapters + LLM + DB + privacy)
sb doctor --privacy             # also scan repo for leaked secrets

sb config show                  # merged config (defaults → user file → env)

sb sync                         # ingest signals from all enabled adapters
sb sync --adapter changelog     # one adapter only
sb sync --since 2026-08-01      # override the cursor

sb signals --since 2026-08-20   # query the evidence ledger
sb signals --domain work --source git --limit 20

sb plan                         # ranked morning brief (dry-run by default)
sb plan --domain work --save    # persist plan_md to sb_daily
sb plan --show-ranker           # display individual score components

sb wrap --dry-run               # evening evidence draft (default)
sb wrap --no-dry-run            # save wrap + queue CHANGELOG proposals
sb wrap --date 2026-08-24       # wrap a past day

sb standup                      # 3-section Yesterday/Today/Blockers

sb review                       # interactively approve/reject pending proposals

sb secret set jira.token        # store secret in Keychain (prompts, hidden)
sb secret list                  # list known secret keys (not values)
sb secret get jira.token        # print a secret value (careful — visible)
```

---

## Install and service management

```bash
sb install --all                # wire all 5 harnesses + launchd + skills
sb install --claude             # just Claude Code
sb install --opencode           # just OpenCode
sb install --cursor             # just Cursor
sb install --vscode             # just VS Code (workspace .vscode/mcp.json)
sb install --launchd            # install + load the sb MCP daemon
sb install --skills             # just the skill/command/agent symlinks

sb mcp serve                    # foreground MCP server (used by launchd)
sb mcp serve --port 8787 --transport sse
```

launchd control (manual):

```bash
launchctl list | grep com.praspr.sb                            # is it loaded?
launchctl unload ~/Library/LaunchAgents/com.praspr.sb.plist    # stop it
launchctl load   ~/Library/LaunchAgents/com.praspr.sb.plist    # start it
tail -f ~/.local/share/sb/service.log                          # server logs
```

---

## Using sb from your coding harness

After `sb install --all`, every MCP-capable harness has these tools:

| Tool | What it does |
|------|-------------|
| `plan_day(domain?, dry_run?)` | Generate today's ranked plan |
| `wrap_day(date?, dry_run?)` | End-of-day evidence draft |
| `standup(date?)` | Async standup (Yesterday/Today/Blockers) |
| `list_tasks(domain?, source?)` | Query the task store |
| `get_task(task_id)` | Full task detail |
| `create_task(title, domain?, priority?, due_date?, sb_ref?)` | Create manual task |
| `complete_task(task_id)` | Mark complete |
| `search_signals(query, since?, source?, domain?)` | Query evidence ledger |
| `get_day(date)` | Retrieve plan+wrap for a specific date |
| `sync_adapters(adapter?)` | Pull latest signals |
| `sync_status()` | Per-adapter health & cursor |
| `list_proposals(status?)` | Approval queue |
| `approve_proposal(id)` | Execute a proposal |
| `reject_proposal(id, reason?)` | Decline a proposal |
| `get_goals(active_only?)` | Load goals (notes stripped) |
| `get_roots()` | Configured folder roots |
| `whoami()` | Resolved identity |

### Skill activation

Each harness has an `sb` skill installed (via symlink):

- Claude Code: `~/.claude/skills/sb/SKILL.md`
- OpenCode: `~/.config/opencode/skills/sb/SKILL.md`
- Cursor: `~/.cursor/skills/sb/SKILL.md`

The skill self-activates when you mention: task planning, morning brief,
end-of-day wrap, standup, JIRA sync, signal search, proposal review.

### Slash commands

Claude Code + OpenCode both have `/plan-day`, `/wrap-day`, `/standup`,
`/sb-ask` commands wired to the sb MCP tools.

---

## Config files to know

### `~/.config/sb/config.yaml`

Personalisation surface. Add or remove folder roots here — no code change needed.

```yaml
identity:
  name: "Your Name"
  emails: [you@example.com]
  git_authors: ["Your Name", "you@example.com"]

roots:
  - path: ~/Documents/code_home/ciq
    label: "Cisco IQ"
    domain: work
    weight: 1.0
    adapters: [changelog, git, jira, tasks]
    jira_projects: [CXP, CXPL]

domains:
  work:     { plan_slots: 3, hours: "09:00-18:00", weekdays_only: true }
  learning: { plan_slots: 1, hours: "19:00-21:00" }
```

### `~/.config/sb/goals.yaml`

Tiered goals — contractual / quarterly / weekly — with keywords for the
ranker's alignment scoring. The `notes` field stays local and is **never**
sent to the LLM.

```yaml
tiers: [contractual, quarterly, weekly]
goals:
  - id: clear_jira_backlog
    tier: weekly
    title: "Keep JIRA assigned queue below 10 open tickets"
    weight: 0.9
    status: active
    keywords: [jira, backlog, ticket, review, triage]
```

Copy the templates:

```bash
mkdir -p ~/.config/sb
cp profiles/config.example.yaml ~/.config/sb/config.yaml
cp profiles/goals.example.yaml  ~/.config/sb/goals.yaml
# edit both
```
