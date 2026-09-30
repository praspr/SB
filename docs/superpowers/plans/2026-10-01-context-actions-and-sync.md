# Context Actions and Scheduled Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add prefilled todo creation from work context, tracked-JIRA removal, and automatic read-only JIRA/Webex pulls.

**Architecture:** Zustand carries a typed todo draft into the existing dialog. JIRA list results expose local tracking state and invoke the existing untrack MCP tool. The existing cron scheduler dispatches the two sync functions and seeds idempotent defaults in core startup.

**Tech Stack:** Python 3.13, FastMCP, SQLite, React, TypeScript, Zustand, TanStack Query, Vitest, pytest.

## Global Constraints

- Atlassian and Webex integrations remain pull-only.
- Tokens remain in Keychain and never enter browser responses or source files.
- Context-created todos use `external_source` and `external_ref` for idempotency.
- Untracking never deletes a mirrored JIRA markdown file.

---

### Task 1: Shared prefilled todo dialog

**Files:**
- Modify: `web/src/lib/store.ts`
- Modify: `web/src/components/tasks/AddTodoDialog.tsx`
- Test: `web/src/components/tasks/AddTodoDialog.test.tsx`

**Interfaces:**
- Produces: `TodoDraft` and `openAddTodo(draft?: TodoDraft)`.
- Consumes: existing `createRichTask` fields.

- [ ] Write a failing test that opens the dialog with a draft and asserts title, description, JIRA ref, and source fields reach `createRichTask`.
- [ ] Run `npm test -- --run src/components/tasks/AddTodoDialog.test.tsx` and confirm failure because draft state is absent.
- [ ] Add draft state/actions and merge draft values into dialog fields when opened.
- [ ] Pass `external_source` and `external_ref` through `createRichTask`.
- [ ] Re-run the focused test and confirm it passes.

### Task 2: Todo actions on JIRA, attention, and meeting proposals

**Files:**
- Modify: `web/src/components/jira/JiraTicketRow.tsx`
- Modify: `web/src/components/attention/AttentionRow.tsx`
- Modify: `web/src/pages/ProposalsPage.tsx`
- Test: corresponding component/page tests.

**Interfaces:**
- Consumes: `openAddTodo(TodoDraft)` from Task 1.
- Produces: buttons labelled `Create todo`.

- [ ] Add failing render/click tests for all three source surfaces.
- [ ] Run focused Vitest files and verify expected missing-button failures.
- [ ] Add source-specific drafts with stable external references and citations.
- [ ] Re-run focused tests and confirm pass.

### Task 3: Tracked JIRA removal

**Files:**
- Modify: `services/jira/src/sb_jira/mcp_tools.py`
- Modify: `web/src/lib/mock-data.ts`
- Modify: `web/src/lib/queries.ts`
- Modify: `web/src/components/jira/JiraTicketRow.tsx`
- Test: `services/jira/tests/test_mcp.py`, `web/src/lib/queries.jira.test.ts`, JIRA row test.

**Interfaces:**
- Produces: ticket field `tracked: bool`.
- Produces: `untrackJira(key)` mutation.

- [ ] Add failing tests asserting tracked flags and `untrack_jira` query invalidation.
- [ ] Run focused tests and verify failures.
- [ ] Decorate list results from `tracking.load_keys()`, add the web mutation, and render Untrack only for tracked rows.
- [ ] Re-run focused tests and confirm pass.

### Task 4: Scheduled JIRA and Webex pulls

**Files:**
- Modify: `services/core/src/sb_core/scheduler.py`
- Modify: `services/core/src/sb_core/mcp_app.py`
- Modify: `web/src/components/layout/SchedulesTab.tsx`
- Test: `services/core/tests/test_scheduler.py`, `web/src/components/layout/SchedulesTab.test.tsx`

**Interfaces:**
- Produces scheduler dispatch names `sync_jira` and `sync_webex`.
- Produces `ensure_default_sync_schedules()`.

- [ ] Add failing tests for dispatch, error propagation, and idempotent defaults.
- [ ] Run scheduler tests and confirm failures.
- [ ] Wrap sync results so non-empty `errors` raise and add both dispatch entries.
- [ ] Seed hourly JIRA and 15-minute Webex schedules during MCP startup.
- [ ] Add both values to `RITUAL_OPTIONS`.
- [ ] Re-run scheduler and Settings tests and confirm pass.

### Task 5: Regression and service restart

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] Document context actions and automatic sync defaults.
- [ ] Run JIRA and core pytest suites.
- [ ] Run the complete web test suite, TypeScript check, and production build.
- [ ] Restart `com.praspr.sb` and verify `/health`.
- [ ] Confirm no hardcoded credentials, certificates, disabled TLS verification, or remote write calls were introduced.
