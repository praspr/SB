# Atlassian MCP Tool Catalog

## Servers

| Server | Harness | Tier | Write support |
|--------|---------|------|---------------|
| `plugin-atlassian-atlassian` | Cursor | A (read-only) | No create/transition |
| `mcp-atlassian` | OpenCode / custom | B (write) | Create, update, transition, comment |

Always call `GetMcpTools` before `CallMcpTool` to inspect current schemas.

## Capability probe

After listing tools, check for write operations:

```
createIssue, transitionIssue, addComment, updateIssue
```

- **Present** → Tier B; create/update workflows allowed
- **Absent** → Tier A; view/search/sync locally only; do not claim JIRA was modified

If `serverStatus` is `needsAuth`, call `mcp_auth` then retry.

## Auth and identity

| Tool | Purpose |
|------|---------|
| `atlassianUserInfo` | Current user (assignee filter, display name) |
| `getAccessibleAtlassianResources` | Resolve `cloudId` for cisco-cxe |
| `mcp_auth` | Authenticate when MCP reports needsAuth |

**cisco-cxe cloudId:** `278247e1-2e3c-4002-bb83-5704fa82bfa0`

## JIRA — read

| Tool | Use when |
|------|----------|
| `getJiraIssue` | Single ticket; pass `fields: ["comment"]` for comments; `responseContentFormat: markdown` |
| `searchJiraIssuesUsingJql` | Bulk fetch; paginate with `nextPageToken`; `maxResults` up to 100 |
| `search` | Natural-language Rovo search (default when user does not say JQL/CQL) |
| `getTransitionsForJiraIssue` | Before status change (write path) |
| `getVisibleJiraProjects` | Pick project for create |
| `getJiraProjectIssueTypesMetadata` | Issue types for project |
| `getJiraIssueTypeMetaWithFields` | Required fields before create — never guess |
| `getJiraIssueRemoteIssueLinks` | External links |
| `getIssueLinkTypes` | Link type names for createIssueLink |
| `lookupJiraAccountId` | Resolve user for assignee |
| `getTeamworkGraphContext` | Cross-entity relationships |
| `getTeamworkGraphObject` | Full object by ARI |
| `fetch` | Fetch issue/page by ARI from search results |

### getJiraIssue example (Cursor)

```json
{
  "server": "plugin-atlassian-atlassian",
  "toolName": "getJiraIssue",
  "arguments": {
    "cloudId": "278247e1-2e3c-4002-bb83-5704fa82bfa0",
    "issueIdOrKey": "CXP-47564",
    "responseContentFormat": "markdown",
    "fields": ["summary", "description", "status", "comment", "assignee", "updated"]
  }
}
```

### searchJiraIssuesUsingJql example

```json
{
  "cloudId": "278247e1-2e3c-4002-bb83-5704fa82bfa0",
  "jql": "assignee = currentUser() ORDER BY updated DESC",
  "maxResults": 100,
  "responseContentFormat": "markdown",
  "fields": ["summary", "description", "status", "issuetype", "priority", "labels", "assignee", "reporter", "created", "updated", "parent"]
}
```

## Confluence — read

| Tool | Use when |
|------|----------|
| `getConfluencePage` | Page by ID; `contentFormat: markdown` for reads |
| `searchConfluenceUsingCql` | CQL search (not JQL) |
| `getConfluenceSpaces` | List spaces |
| `getPagesInConfluenceSpace` | Pages in a space |
| `getConfluencePageDescendants` | Child pages |
| `getConfluencePageFooterComments` | Page comments |
| `getConfluencePageInlineComments` | Inline comments |
| `getConfluenceCommentChildren` | Comment replies |

## Post-MCP action (always)

Sync results to `/Users/praspr/Documents/code_home/ciq/docs/jira/` per docs-only 4-file protocol in `SKILL.md`.
