# Write MCP Setup — Tier B

Use when create, transition, or comment on JIRA issues is required.

Cursor's `plugin-atlassian-atlassian` is **read-only**. For writes, configure **mcp-atlassian**:

- https://github.com/sooperset/mcp-atlassian

## Environment variables (never commit)

```bash
export ATLASSIAN_URL=https://cisco-cxe.atlassian.net
export ATLASSIAN_USERNAME=<cisco-email>
export ATLASSIAN_API_TOKEN=<api-token-from-id.atlassian.com>
```

Generate API token: https://id.atlassian.com/manage-profile/security/api-tokens

## OpenCode example (opencode.json)

```json
{
  "mcp": {
    "atlassian": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-atlassian"],
      "env": {
        "ATLASSIAN_URL": "https://cisco-cxe.atlassian.net",
        "ATLASSIAN_USERNAME": "${ATLASSIAN_USERNAME}",
        "ATLASSIAN_API_TOKEN": "${ATLASSIAN_API_TOKEN}"
      }
    }
  }
}
```

## Create issue workflow

1. `getVisibleJiraProjects` → select `CXP` or `CXPL`
2. `getJiraProjectIssueTypesMetadata` → select Story/Bug/Epic/etc.
3. `getJiraIssueTypeMetaWithFields` → list **required** fields only
4. Submit create via write MCP with discovered field schema
5. Capture returned issue key
6. Sync to `docs/jira/` (4-file protocol)
7. Optionally post PM plan as JIRA comment

## Update issue workflow

1. `getJiraIssue` — baseline snapshot
2. `getTransitionsForJiraIssue` — pick valid `transitionId` (never guess status names)
3. Apply transition or field update via write MCP
4. Re-fetch issue; diff changed fields
5. Append `docs/jira/tickethistory.md` with **Last Updated On**
6. Update `docs/jira/tickets/{KEY}.md` and `README.md`

## Confluence write

Write tools vary by MCP version. Probe tool list before create/update page.
Read path always works on Tier A.

## Failure handling

- If write fails → sync local draft only; tell user what to paste in JIRA UI
- Never claim success without re-fetch confirmation
- Never hardcode credentials in skill files, scripts, or repo
