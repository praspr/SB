---
name: todos
description: Manages local todos when listing, searching, creating, updating, completing, or deleting tasks.
---

# Todos

## Allowed tools
- `todo_list`
- `todo_get`
- `todo_add`
- `todo_complete`
- `todo_uncomplete`
- `todo_update`
- `todo_delete`
- `todo_search`

## Procedure
1. Use `todo_list` or `todo_search` to locate existing work before creating duplicates.
2. Use `todo_get` when full details are needed.
3. Confirm the intended task and fields before a destructive `todo_delete`.
4. Use only the allowed tools above for todo operations.
5. Report the resulting todo id and status after a mutation.
