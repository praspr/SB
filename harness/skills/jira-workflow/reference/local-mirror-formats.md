# Local Mirror Formats — docs/jira only

## Canonical root

```
/Users/praspr/Documents/code_home/ciq/docs/jira/
```

**Do not write ticket data anywhere else.**

## Active-only mirror policy

Local files exist only for **non-terminal** JIRA statuses. On sync:

- **Keep:** Open, Code Review, Dev Complete, In Testing, Test Complete, Blocked, etc.
- **Purge:** Closed, Done, Cancelled — delete `tickets/{KEY}.md`, omit from index
- **Archive:** append **Removed** row to `tickethistory.md` with one-line summary

JIRA browse links remain valid after purge.

## Directory layout

```
docs/
├── README.md              ← step 4: folder map + quick link to jira/
└── jira/
    ├── README.md          ← step 2: index table (active tickets only)
    ├── tickethistory.md   ← step 3: audit log (includes Removed summaries)
    └── tickets/
        └── CXP-XXXXX.md   ← step 1: per-ticket file (active only)
```

## Index table (docs/jira/README.md)

Header block:

```markdown
# JIRA Tickets — <Assignee or scope>

> **Last synced:** YYYY-MM-DD
> **Source:** https://cisco-cxe.atlassian.net
> **Policy:** Closed/Done/Cancelled tickets removed from mirror; summaries in tickethistory.md

## Ticket index (N active tickets)

| File | Ticket | Title | Status | Type | Updated |
|------|--------|-------|--------|------|---------|
```

- Sort by Updated descending
- Truncate long titles to ~70 chars in index
- Status column uses emoji labels from SKILL.md
- Count **N** = active tickets only (not JIRA assignee total if some are closed)

## tickethistory.md

```markdown
# JIRA Sync History — docs/jira

| Date | Ticket | Change Type | Last Updated On | Description |
|------|--------|-------------|-----------------|-------------|
```

Append rows; group bulk syncs with HTML comment:

```markdown
<!-- Bulk sync YYYY-MM-DD -->
<!-- Closed ticket purge YYYY-MM-DD -->
```

**Removed** rows are the archive for purged tickets — do not delete these when cleaning old **Synced** rows.

## Ticket file

See [`ticket_template.md`](ticket_template.md). Filename: `{KEY}.md` (e.g. `CXP-47564.md`).

## Do NOT write

| Path | Reason |
|------|--------|
| `JIRA/` at repo root | Deprecated |
| `JIRA/CLAUDE.md` | Superseded by `docs/jira/README.md` |
| Root `CLAUDE.md` JIRA table | Superseded |
| `{other-repo}/docs/jira/` | Wrong repo |
| Any path outside `ciq/docs/` | Violates single-store rule |
| `tickets/{KEY}.md` for Closed/Done/Cancelled | Purge on sync |

## Confluence mirrors (optional)

```
/Users/praspr/Documents/code_home/ciq/docs/confluence/
```

Not ticket data — separate from `docs/jira/`.

## CHANGELOG

After any edit under `docs/jira/`, append root `CHANGELOG.md`:

```markdown
## [YYYY-MM-DD]
- **Updated** docs/jira — <what changed> — *`docs`*
```
