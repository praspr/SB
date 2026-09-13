# sb — Architecture Summary

## Layered design

```
┌── ADAPTERS (each optional, config-driven) ────────────────────────┐
│   changelog · git · jira · tasks_local · outlook* · webex*        │
│           walk config.roots[], respect scan.exclude[]              │
│                                                                    │
│   *Phase 3 (not yet built)                                         │
└───────────────────────────┬───────────────────────────────────────┘
                            │  emit Signal[] (normalised envelope)
┌───────────────────────────▼───────────────────────────────────────┐
│ CORE                                                              │
│  ingest → dedupe on (source, source_id) → link JIRA/repo/people   │
│  persist to sb_signals in TodoLocal SQLite (WAL mode)              │
│                                                                    │
│  STORE:  ~/Library/Application Support/TodoLocal/todo.db          │
│          sb_* tables + additive sb_* columns on existing `tasks`  │
│          coexists with todoist-local GUI (57/57 tests pass)       │
└───────────────────────────┬───────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│ BRAIN (claudegate :9999, OpenAI-compatible, Copilot backend)      │
│                                                                    │
│  rank.py   pure scoring (RICE + Eisenhower + WLB, no LLM)         │
│  plan.py   synthesize morning brief (smart tier)                   │
│  wrap.py   evidence harvest + gap questions + proposals (smart)   │
│  llm.py    tiered client (fast/smart/deep) + cache + cost log     │
│                                                                    │
│  Tiers: fast=gpt-5-mini · smart=claude-sonnet-4.6 · deep=opus-4.8 │
└───────────────────────────┬───────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│ SURFACES  (all call same core — no logic divergence)              │
│                                                                    │
│  CLI:     sb doctor|sync|signals|plan|wrap|standup|review|...     │
│  MCP:     FastMCP SSE :8787 (15 tools) — used by all harnesses    │
│  launchd: com.praspr.sb — always-on daemon, KeepAlive=true        │
│  install: symlinks skills, commands, agents into 3 harness dirs   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Data model

### Signal (evidence ledger)

Every observed fact from any adapter becomes a Signal. Append-only,
deduplicated on `(source, source_id)`. This is the ground truth that
`wrap_day` cites when it drafts "what I did today".

```
source       changelog | git | jira | webex | outlook | tasks | manual
source_id    stable dedup key within source (SHA, CXP-N, message id)
kind         commit | changelog_entry | ticket | message | meeting | email
occurred_at  ISO-8601 UTC
title        one-line summary
body         fuller content (optional)
scope        e.g. "configbp-ai" or "CXP-45827"
verb         Added | Updated | Fixed | feat | fix | …
refs         {jira: [], repos: [], people: []}
raw_ref      path#L42 or URL — back to ground truth
```

### Task (planning unit)

Wraps todoist-local's `tasks` table with `sb_*` additive columns:

```
sb_source    jira | changelog | git | webex | outlook | manual
sb_ref       CXP-45827
sb_url       deep link
sb_domain    work | learning | personal
sb_root      root label from config
sb_energy    deep | shallow | meeting
sb_score     last ranker score
sb_rationale audit string — why this rank
```

Idempotent upsert on `(sb_source, sb_ref)` — same JIRA sync twice creates
no duplicate tasks.

### DailyEntry

One row per calendar day in `sb_daily`. Holds `plan_md`, `plan_data`,
`wrap_md`, `wrap_data`, timestamps, notes. Written by `plan_day` and
`wrap_day`.

### Proposal (approval queue)

Nothing remote ever fires without approval. `sb_proposals` queues:

- CHANGELOG entries drafted by `wrap`
- JIRA transitions/comments (future)
- Webex replies (future)
- Email drafts (future)

Status flow: `pending → approved → executed` or `pending → rejected`.

---

## Config-driven scope

`~/.config/sb/config.yaml` is the entire personalisation surface. To
add a folder to scanning: edit `roots:`. No code change.

```yaml
roots:
  - path: ~/Documents/code_home/ciq
    label: "Cisco IQ"
    domain: work
    weight: 1.0
    adapters: [changelog, git, jira, tasks]
    jira_projects: [CXP, CXPL]
    scan: {max_depth: 3}
```

Global exclude list prevents scanner runaway:

```yaml
scan:
  exclude: [.venv, node_modules, site-packages, __pycache__, .git/objects, dist, build]
  max_file_mb: 5
```

---

## Skill reuse principle

sb never reimplements a skill's workflow — it provides **data**,
existing skills provide **procedure**.

| Existing skill | Relationship to sb |
|----------------|---------------------|
| `jira-workflow` | Authoritative for the `docs/jira/` 4-file protocol; sb's JIRA adapter feeds it |
| `git-workflow` | Owns the CHANGELOG format; `wrap_day` drafts entries in that exact format |
| `reflect` | Weekly/pattern-level; sb feeds it via `search_signals()` |
| `python-dev` | Governs sb's own build (uv, pytest, black/flake8/mypy) |
| `graphify` | Phase 3+: `sb_signals` as graph input |

---

## Autonomy contract

**Propose, don't act.**

| Action | sb behaviour |
|--------|-------------|
| Local writes (task complete, daily entry, signal insert) | ✅ Automatic |
| CHANGELOG proposals | ⏸ Queued in `sb_proposals`, need `sb review` approve |
| JIRA transitions/comments | ⏸ Queued as proposals (Phase 2) |
| Webex replies, email sends | ⏸ Queued as proposals (Phase 3) |

The user is always the final actor for anything with side effects
outside the local machine.

---

## Reliability guarantees

- **Coexistence:** all sb migrations are additive-only, `sb_`-prefixed,
  and numbered 900+ to never collide with todoist-local's sequence.
  Verified by todoist-local's own 57/57 tests running against a
  post-migration DB.
- **Isolated failure:** each adapter runs with a timeout inside
  `run_adapter()`; one broken adapter never fails the whole sync.
- **Idempotent sync:** signals are deduplicated on `(source, source_id)`;
  re-running `sb sync` never creates duplicates.
- **Content-hash LLM cache:** identical prompt+model → cache hit; zero
  tokens billed on retry.
- **Approval queue:** all remote actions gated behind explicit `sb review`.
- **Privacy scan:** `sb doctor --privacy` fails if any Cisco/personal
  strings leaked into tracked files.
