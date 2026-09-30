# tickethistory row template

Append to `/Users/praspr/Documents/code_home/ciq/docs/jira/tickethistory.md`:

```markdown
| {sync_date} | {KEY} | **{ChangeType}** | {jira_updated_utc} | {description} |
```

## Fields

| Field | Example | Source |
|-------|---------|--------|
| sync_date | `2026-08-19` | Today (local edit date) |
| KEY | `CXP-47564` | Issue key |
| ChangeType | `Synced` | Created / Synced / **Removed** / Status Update / … |
| jira_updated_utc | `2026-08-19 05:58:14 UTC` | JIRA `fields.updated` (UTC, no ms) |
| description | `Pulled from JIRA. Status: Open.` | Human-readable one-liner |

## Removed row (closed-ticket purge)

When JIRA status is **Closed**, **Done**, or **Cancelled**:

```markdown
| 2026-08-25 | CXP-45827 | **Removed** | 2026-08-24 04:41:53 UTC | Closed (Fixed). SH Result filter ignored on per-asset table; BAQS PR #149. |
```

- Delete `docs/jira/tickets/{KEY}.md`
- Omit from `README.md` index
- **Removed** description = status + resolution + short title gist (≤ ~120 chars)

## Format JIRA updated timestamp

From `2026-08-19T05:58:14.041+0000` → `2026-08-19 05:58:14 UTC`
