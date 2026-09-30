---
name: context
description: Loads identity, project roots, and goals when work needs local operating context.
---

# Context

## Allowed tools
- `whoami`
- `get_roots`
- `get_goals`

## Procedure
1. Use `whoami` only when identity or ownership affects the task.
2. Use `get_roots` to resolve configured project locations instead of guessing paths.
3. Use `get_goals` when prioritization or alignment depends on stated goals.
4. Return only the context needed for the current request.
