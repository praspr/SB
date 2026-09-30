---
name: jira
description: Browses and refreshes the local JIRA markdown mirror when ticket context or status is needed.
---

# JIRA

## Allowed tools
- `list_jira_tickets`
- `get_jira_ticket`
- `sync_jira`
- `jira_status`

## Procedure
1. Use `jira_status` to check local mirror health when freshness is uncertain.
2. Use `list_jira_tickets` to filter the local mirror, then `get_jira_ticket` for full detail.
3. Use `sync_jira` only when a refresh is requested or stale data is material.
4. `sync_jira` pulls Atlassian data into local files; it never writes to Atlassian.
5. Treat JIRA as pull-only and propose any remote update without executing it.
