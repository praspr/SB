# sb-jira

Pull-only library for the local JIRA markdown mirror. `sb-core` mounts its
MCP tools in-process. This package does not run its own HTTP server and never
writes to Atlassian.

## Tools

On `http://127.0.0.1:8787/mcp`:

- `list_jira_tickets` — filter the local mirror
- `get_jira_ticket` — one ticket, including sections
- `sync_jira` — pull Atlassian into local files only
- `jira_status` — ticket count, last local sync, and a read-only reachability probe

`GET /health` on sb-core does not call Atlassian.

## Config

Paths are overridable with `SB_JIRA_*` (see `src/sb_jira/config.py`), including
`SB_JIRA_TICKETS_DIR`.

The Atlassian API token is read from the macOS Keychain via `keyring`
(service `sb`, account `jira.token`) or from the `ATLASSIAN_API_TOKEN`
environment variable. It is never written into the repo. If no token is
configured, `sync_jira` returns an error entry and does not change ticket files.

## Tests

```bash
cd sb/services/jira
.venv/bin/python -m pytest -q
```
