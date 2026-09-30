# sb-todos

SQLite todo handlers and MCP tools. This package is a library mounted
in-process by `sb-core`. It does not run its own HTTP server.

## Storage

SQLite database at `~/.local/share/sb/todos.db` (parent directories are
created automatically on first connection). WAL journal mode,
`busy_timeout=5000`, foreign keys on.

Override the path with `SB_TODOS_DB_PATH`.

Each MCP tool opens a fresh connection and closes it before returning.
Connections stay on the thread that opened them.

## MCP tools

Mounted on the unified `sb` server at `http://127.0.0.1:8787/mcp` with
their original names:

`todo_list`, `todo_get`, `todo_add`, `todo_complete`, `todo_uncomplete`,
`todo_update`, `todo_delete`, `todo_search`.

There is no `/api/todos` surface.

## Idempotent external upsert

`todo_add` accepts optional `external_source` + `external_ref` (for example
`"jira"` / `"CXP-45827"`). If a todo with that pair already exists, it is
updated in place. That is enforced by `handlers.add_todo` and by the unique
partial index `idx_todos_ext`.

## Tests

```bash
cd sb/services/todos
.venv/bin/python -m pytest -q
```

- `test_db.py` — migrations, columns, idempotence
- `test_handlers.py` — CRUD, search, external-ref upsert
- `test_mcp.py` — all eight tools are registered with descriptions

## Project layout

```
sb/services/todos/
├── pyproject.toml
├── README.md
├── src/sb_todos/
│   ├── config.py
│   ├── models.py
│   ├── db.py
│   ├── migrations/001_init.sql
│   ├── handlers.py
│   └── mcp_tools.py
└── tests/
```
