---
name: wrap
description: Produces an evidence-backed day wrap when summarizing outcomes, gaps, and proposed follow-ups.
---

# Wrap

## Allowed tools
- `wrap_day`
- `search_signals`

## Procedure
1. Search for evidence of completed work, changes, blockers, and unresolved items.
2. Cite every factual outcome with returned evidence in `[signal:N]` form; never invent evidence.
3. Use `wrap_day` in dry-run mode unless the user explicitly requests another supported mode.
4. Separate confirmed outcomes from inferred or missing information.
5. Propose follow-ups; do not act on todos, JIRA, changelogs, or other remote systems.
