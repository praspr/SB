---
name: plan
description: Builds an evidence-backed daily plan when prioritizing goals, todos, and recent signals.
---

# Plan

## Allowed tools
- `plan_day`
- `get_goals`
- `todo_list`
- `search_signals`

## Procedure
1. Load goals and open todos, then search for current evidence.
2. Rank work by urgency, impact, dependencies, and available time.
3. Cite factual rationale with returned evidence in `[signal:N]` form; never invent evidence.
4. Use `plan_day` to assemble the proposed sequence and identify trade-offs.
5. Propose changes; do not act on todos, JIRA, changelogs, or other remote systems.
