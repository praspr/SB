---
name: jira-workflow
description: >
  Atlassian JIRA and Confluence workflow for Cisco IQ — view, search, sync,
  create, and update tickets via MCP. All local ticket data is stored only
  under /Users/praspr/Documents/code_home/ciq/docs/jira/.
  Use when the user mentions JIRA, CXP-/CXPL- tickets, Confluence, JQL, CQL,
  ticket sync, Atlassian MCP, or docs/jira/.
---

# JIRA Workflow — Cisco IQ (Atlassian MCP + Local Mirror)

## Canonical local store (mandatory)

```text
CIQ_DOCS_ROOT=/Users/praspr/Documents/code_home/ciq/docs
CIQ_JIRA_ROOT=/Users/praspr/Documents/code_home/ciq/docs/jira
```

| Path | Purpose |
|------|---------|
| `docs/jira/tickets/{KEY}.md` | One file per ticket |
| `docs/jira/README.md` | Ticket index table |
| `docs/jira/tickethistory.md` | Sync/change audit log |
| `docs/README.md` | Docs folder map — must link to `jira/` |

**Hard rules:**

- **Always read** ticket context from `CIQ_JIRA_ROOT` before answering
- **Always write** ticket creates/updates/syncs to `CIQ_JIRA_ROOT` only
- **Never** write ticket files under repo-root `JIRA/`, other repos, or paths outside `ciq/docs/`
- **Never** update root `CLAUDE.md` `## JIRA Tickets` for ticket storage (superseded by `docs/jira/README.md`)
- Confluence mirrors (if saved) go under `docs/confluence/` only
- Update root `CHANGELOG.md` when ciq repo docs change (repo hygiene, not ticket storage)
- **Closed-ticket purge (mandatory on sync):** do not keep local mirror files for terminal statuses — see [Closed-ticket purge](#closed-ticket-purge-mandatory-on-sync)

**Legacy (deprecated — do not write):** `JIRA/CXP-*.md`, `JIRA/CLAUDE.md`, `JIRA/tickethistory.md`. Migrate to `docs/jira/` on sync.

---

## MCP startup checklist

Run before any JIRA/Confluence action:

1. **Discover tools** — `GetMcpTools` for `plugin-atlassian-atlassian` (or write MCP). Always inspect schema before `CallMcpTool`.
2. **Auth** — `atlassianUserInfo`. If auth fails, call `mcp_auth` and retry.
3. **cloudId** — `getAccessibleAtlassianResources` → cache ID for cisco-cxe (`278247e1-2e3c-4002-bb83-5704fa82bfa0`).
4. **Capability probe** — if no `createIssue` / `transitionIssue` (or equivalent) → **Tier A read-only**. State clearly before claiming create/update succeeded.

Details: [`reference/mcp-tools.md`](reference/mcp-tools.md)

### Instance constants

| Constant | Value |
|----------|-------|
| Site | `https://cisco-cxe.atlassian.net` |
| Projects | `CXP` (features), `CXPL` (platform perf) |
| Issue URL | `https://cisco-cxe.atlassian.net/browse/{KEY}` |

---

## View and search

| Task | Tool | When |
|------|------|------|
| Single issue | `getJiraIssue` | One key; add `fields: ["comment"]` for comments |
| Bulk JQL | `searchJiraIssuesUsingJql` | Paginate with `nextPageToken` (max 100/page) |
| Natural language | `search` (Rovo) | Default unless user says JQL/CQL |
| Transitions | `getTransitionsForJiraIssue` | Before status change (write path) |
| Confluence page | `getConfluencePage` | `contentFormat: markdown` for reads |
| Confluence search | `searchConfluenceUsingCql` | User specifies CQL |
| Spaces / pages | `getConfluenceSpaces`, `getPagesInConfluenceSpace` | Browse hierarchy |

JQL/CQL recipes: [`reference/jql-recipes.md`](reference/jql-recipes.md), [`reference/cql-recipes.md`](reference/cql-recipes.md)

---

## Docs-only 4-file protocol (mandatory)

Every ticket create, update, or sync from JIRA requires **all four**:

| Step | File | Action |
|------|------|--------|
| **1** | `docs/jira/tickets/CXP-XXXXX.md` | Create or update ticket markdown |
| **2** | `docs/jira/README.md` | Update index row (status emoji, title, updated date) |
| **3** | `docs/jira/tickethistory.md` | Append row with **Last Updated On** |
| **4** | `docs/README.md` | Ensure `jira/` entry in folder map / quick links |

**Never update only the ticket file.**

### tickethistory row format

```markdown
| Date | Ticket | Change Type | Last Updated On | Description |
```

- **Date** = local sync/edit date (`YYYY-MM-DD`)
- **Last Updated On** = JIRA `fields.updated` as `YYYY-MM-DD HH:MM:SS UTC`
- **Change Types:** `Synced` / `Created` / `Removed` / `Status Update` / `Requirement Change` / `Assignee Change` / `Priority Change` / `Comment Added`
- **`Removed`** = local `tickets/{KEY}.md` deleted because JIRA status is terminal; one-line summary retained in this log

Template: [`templates/tickethistory-row.md`](templates/tickethistory-row.md)

---

## Status emoji mapping (index tables)

| JIRA status | Index label |
|-------------|-------------|
| Open | `📋 Open` |
| Closed, Done, Cancelled | `✅ Closed` |
| In Engineering Review, Concept Approved, Code Review, Dev Complete, In Testing, Test Complete, Blocked | `🔶 In Engineering Review` |

Metadata table inside ticket files uses **plain status name** (no emoji).

---

## Ticket file format

Template: [`reference/ticket_template.md`](reference/ticket_template.md)

```
# CXP-XXXXX — <Title>
| Field | Value |   ← metadata table
---
## Context
## Feature Description / Requirements
## Acceptance Criteria   ← if present in JIRA
## Notes
```

Optional for jira-manager: `## Delivery Plan` after Acceptance Criteria.

---

## Closed-ticket purge (mandatory on sync)

The local mirror holds **active work only**. Terminal JIRA statuses are removed from disk; summaries live in `tickethistory.md`.

| JIRA status | Local mirror file | Index row |
|-------------|-------------------|-----------|
| Open, Code Review, In Testing, Test Complete, Blocked, … | **Keep** (create/update) | **Keep** |
| **Closed**, **Done**, **Cancelled** | **Delete** `tickets/{KEY}.md` | **Omit** |
| | Append **`Removed`** row to `tickethistory.md` | |

**Removed row description:** one line — title gist + resolution (e.g. `Closed (Fixed). SH Result filter bug; BAQS PR #149.`). JIRA browse URL still works after purge.

**On every sync (bulk or single):**

1. If fetched status is terminal → delete local file (if present), append **Removed**, skip ticket write
2. If active → write/update ticket file, append **Synced** (or **Created**)
3. Regenerate `README.md` from **active tickets only** (on-disk files + current sync batch)
4. Optional safety scan: any remaining `tickets/*.md` whose `**Status**` is Closed/Done/Cancelled → purge + **Removed**

Helper script implements steps 1–4: [`scripts/sync_assigned_tickets.py`](scripts/sync_assigned_tickets.py)

---

## Sync workflow (bulk or single)

1. Fetch via MCP (`getJiraIssue` or `searchJiraIssuesUsingJql`)
2. **Purge** terminal statuses; write/update active `docs/jira/tickets/{KEY}.md` only
3. Regenerate `docs/jira/README.md` index — active tickets only, sort by `updated` desc
4. Append `docs/jira/tickethistory.md` rows (**Synced** / **Created** / **Removed**; include **Last Updated On**)
5. Confirm `docs/README.md` links to `jira/` (update ticket count if bulk purge)
6. Update root `CHANGELOG.md`

Helper script: [`scripts/sync_assigned_tickets.py`](scripts/sync_assigned_tickets.py)

Full layout: [`reference/local-mirror-formats.md`](reference/local-mirror-formats.md)

---

## Create / update via MCP (write path)

### Tier A — Read-only (Cursor `plugin-atlassian-atlassian`)

Allowed: view, search, sync locally, draft ticket text for manual JIRA entry.

Blocked: create, transition, comment, Confluence write. Say: *"Write tools unavailable; synced locally only."*

### Tier B — Write-capable (`mcp-atlassian`)

Setup: [`reference/write-mcp-setup.md`](reference/write-mcp-setup.md)

**Create:** project → issue type → `getJiraIssueTypeMetaWithFields` → create → sync to `docs/jira/`

**Update:** `getJiraIssue` → `getTransitionsForJiraIssue` → apply → re-fetch → sync to `docs/jira/`

---

## Confluence

- **Read:** MCP tools above; optional summary template [`templates/confluence-page-summary.md`](templates/confluence-page-summary.md)
- **Local mirror:** `docs/confluence/{page-id}-{slug}.md` (within `CIQ_DOCS_ROOT` only)
- **Write:** gated on Tier B MCP; probe before attempting

---

## Worked example — sync one ticket

User: "Sync CXP-47564 from JIRA"

1. `getJiraIssue` with `issueIdOrKey: CXP-47564`, `responseContentFormat: markdown`
2. Write `docs/jira/tickets/CXP-47564.md`
3. Update row in `docs/jira/README.md`
4. Append to `docs/jira/tickethistory.md`:
   `| 2026-08-19 | CXP-47564 | **Synced** | 2026-08-19 05:58:14 UTC | Pulled from JIRA. Status: Open. |`
5. Verify `docs/README.md` has jira link
6. `CHANGELOG.md` entry if files changed

---

## Reference index

| File | Contents |
|------|----------|
| [`reference/mcp-tools.md`](reference/mcp-tools.md) | Full MCP tool catalog + capability probe |
| [`reference/jql-recipes.md`](reference/jql-recipes.md) | Common JQL |
| [`reference/cql-recipes.md`](reference/cql-recipes.md) | Common CQL |
| [`reference/write-mcp-setup.md`](reference/write-mcp-setup.md) | Tier B write MCP |
| [`reference/local-mirror-formats.md`](reference/local-mirror-formats.md) | docs/jira layout only |
| [`reference/ticket_template.md`](reference/ticket_template.md) | Per-ticket template |

---

## When to update this skill

- New JIRA status emoji mapping
- Terminal status list for closed-ticket purge
- MCP tool or cloudId changes
- Ticket file format changes
- `CIQ_JIRA_ROOT` path changes
