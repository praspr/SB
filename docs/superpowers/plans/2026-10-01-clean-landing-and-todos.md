# Clean Landing and Todos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a minimal daily landing page and a structured, more useful Todos page.

**Architecture:** Keep existing queries and mutations intact. Extract pure todo grouping and filtering helpers for deterministic tests, compose the landing page from existing task and meeting rows, and make chat expandable so it does not dominate the default layout.

**Tech Stack:** React 18, TypeScript, TanStack Query, Tailwind CSS, Vitest.

## Global Constraints

- Frontend-only; preserve MCP contracts and mutations.
- Add no dependencies.
- Preserve JIRA import and todo metadata.
- Keep responsive layouts and the existing dark theme.

---

### Task 1: Define the landing hierarchy

**Files:**
- Create: `web/src/pages/LandingPage.test.tsx`
- Modify: `web/src/pages/LandingPage.tsx`
- Modify: `web/src/components/landing/ChatPanel.tsx`

**Interfaces:**
- Consumes: existing `useTodayTasks`, `useTodayMeetings`, and `useWebexAttention`.
- Produces: a landing view with attention, top todos, upcoming meetings, and expandable chat.

- [ ] Write a rendering test asserting the core section labels exist and Usage, ledger deltas, and dashboard status summaries do not.
- [ ] Run `npm test -- --run src/pages/LandingPage.test.tsx` and verify the test fails against the current page.
- [ ] Replace the repeated dashboard sections with the approved minimal hierarchy and compact assistant.
- [ ] Re-run the focused test and verify it passes.

### Task 2: Add deterministic todo organization

**Files:**
- Create: `web/src/lib/todo-groups.ts`
- Create: `web/src/lib/todo-groups.test.ts`

**Interfaces:**
- Consumes: `Task[]`, status, priority, search, and sort inputs.
- Produces: summary counts and labeled task groups.

- [ ] Write tests for overdue/today/upcoming/no-date/completed grouping, filtering, and sorting.
- [ ] Run `npm test -- --run src/lib/todo-groups.test.ts` and verify failure because the helper is absent.
- [ ] Implement the pure helper with local-date comparisons.
- [ ] Re-run the focused test and verify it passes.

### Task 3: Redesign the Todos page

**Files:**
- Modify: `web/src/pages/TodosPage.tsx`
- Modify: `web/src/pages/TodosPage.test.tsx`
- Modify: `web/src/components/tasks/TaskRow.tsx`

**Interfaces:**
- Consumes: grouping helper from Task 2 and existing rich todo/JIRA queries.
- Produces: summary strip, search/sort/filter toolbar, and grouped task sections.

- [ ] Extend the page test to assert summary labels, search, sort, and grouped sections.
- [ ] Run the focused page test and verify it fails.
- [ ] Implement the grouped productivity layout while preserving the import dialog.
- [ ] Re-run the focused page test and verify it passes.

### Task 4: Verify the web application

**Files:**
- Modify: `CHANGELOG.md`

- [ ] Run `npm test -- --run`.
- [ ] Run `npx tsc --noEmit`.
- [ ] Run `npm run build`.
- [ ] Check edited files for IDE lint errors.
- [ ] Add a concise changelog entry and confirm `git diff --check`.
