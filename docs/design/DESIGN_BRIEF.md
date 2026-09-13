# sb dashboard — Design Brief

## What this is

`sb dashboard` is the macOS-first React UI for `sb`, the local second-brain chief-of-staff assistant. It is not a chat app. It is an operational dashboard that turns the existing `sb` backend into a fast, dense, keyboard-first control surface for planning, evidence review, proposal approval, and adapter health.

The shell is designed so future personal-assistant areas — finance, health, reading list, home automation — install as sidebar apps without changing the chief-of-staff foundation.

## Who it is for

- A single local user already running `sb` on macOS
- Someone who works across code, changelogs, JIRA, and local tasks
- Someone who wants structured assistance, not a persistent chat thread

## Product facts that drive the design

| Backend fact | UI consequence |
|---|---|
| `sb` already exposes 15 MCP tools over SSE on `127.0.0.1:8787/sse` | The app should be a thin client over MCP, not a second business-logic layer |
| Core objects are `Signal`, `Task`, `Proposal`, `DailyEntry`, `Goal` | Navigation and components should map directly to those objects |
| All remote actions are approval-gated | Proposals need first-class visibility, exact payload review, and fast approve/reject actions |
| Evidence is the system of record with `[signal:N]` citations | Citations must be clickable everywhere, especially wrap + plan views |
| Sync is adapter-based and partially optional | Adapter status needs its own screen with cursor, last run, and failure detail |
| The current surface is CLI + MCP only | The UI should expose the full MCP tool surface with minimal interpretation |

## Product principles

1. **Dashboard first.** Open on Today, not on chat.
2. **Structured over conversational.** Use lists, detail panels, score breakdowns, and flyouts.
3. **Keyboard first.** `⌘K` is the control center; row actions also work from the keyboard.
4. **Evidence before opinion.** Every summary should link back to signals.
5. **Dense, not cramped.** Linear-style information density with disciplined spacing.
6. **Future apps fit the same shell.** Chief of Staff is the first app, not the only app.
7. **Local trust model stays visible.** Show what is local, what is synced, and what still needs approval.

## Design language

The design is intentionally close to Linear in its operating feel because the product constraints point there directly: muted grays, sharp typography, single-accent focus, strong keyboard support, compact rows, and restrained motion.

Why this fits `sb`:

- The backend is already highly structured, with exact tool calls and exact object types.
- The user asked for data-forward interaction and no persistent chat panel.
- Proposal review, score ranking, and signal citations all work better in a dense app shell than in a conversational canvas.
- A localhost dashboard on macOS benefits from a desktop-like, sidebar-first layout.

## Information architecture

### Shell level

- **Sidebar app registry**
  - Chief of Staff
  - Future: Finance, Health, Reading, Home
- **Per-app routes**
  - Chief of Staff owns Today, Tasks, Signals, Proposals, Goals, Adapters, Settings

### Chief of Staff views

| View | MCP tools surfaced |
|---|---|
| Today | `plan_day`, `wrap_day`, `get_day`, `standup`, `search_signals` |
| Tasks | `list_tasks`, `get_task`, `create_task`, `complete_task` |
| Signals | `search_signals`, `get_day` |
| Proposals | `list_proposals`, `approve_proposal`, `reject_proposal` |
| Goals | `get_goals`, `list_tasks`, `get_day` |
| Adapters | `sync_status`, `sync_adapters`, `get_roots` |
| Settings | `whoami`, `get_roots`, `sync_status` plus local config/secrets UI hooks |

## Primary surfaces

### 1) Full dashboard

The main browser/PWA surface. This is the daily driver. It uses a fixed left rail, compact top bar, and main content area that can switch between split views and list/detail views.

### 2) Menu bar quick view

A narrow popover-sized surface for the morning glance:

- top 3 must-dos with score
- one primary `Wrap now` action
- adapter health dot
- click-through to full dashboard

This uses the same data layer and the same route tree, but a different layout profile.

### 3) PWA

The dashboard installed to the Dock. Same app, same routes, standalone display mode, no browser chrome, stronger “native utility” feel.

## Interaction model

### Command palette as control plane

`⌘K` is the single global launcher for:

- Rituals: Plan today, Wrap today, Standup
- Sync: Sync all, sync one adapter
- Tasks: New task, mark done, find task
- Signals: Search signals
- Proposals: Approve next, reject next
- Navigation: Jump to any view
- Settings: Open config, secrets, harness status

Because the backend already exposes exact MCP actions, the palette should call those actions directly and then invalidate the right cached queries.

### No persistent chat panel

Any LLM-backed output appears as a structured result:

- morning plan cards
- wrap summary sections
- standup block
- proposal payload preview

This keeps the build practical in React and aligned with the current backend.

## Screen-by-screen intent

### Today

- Default landing screen
- Two columns: morning plan on the left, evening wrap on the right
- Most recent `DailyEntry` visible immediately
- Strong action cluster: Plan today, Wrap today, Standup, Sync all
- Citation flyout for `[signal:N]`

### Tasks

- Ranked task list with score, score bar, source, domain, due state
- Filters for domain and source because `sb` stores both
- Quick complete with optimistic state change

### Signals

- Evidence timeline with filter chips for source, scope, date range, domain, query
- Detail flyout shows `raw_ref`, linked refs, body, and related task/proposal context

### Proposals

- Approval queue centered on exact text payloads
- Keyboard actions: `A` approve, `R` reject, `S` skip
- Optimistic row transitions because approve/reject are common repeat actions

### Goals

- Tiered columns: contractual → quarterly → weekly
- Alignment surfaces tasks and plans influenced by each goal
- Makes keyword-based ranker output understandable

### Adapters

- Operational health screen for each adapter
- Cursor, last success, last error, root coverage, one-click resync

### Settings

- Utility screen for identity, roots, goals file locations, secrets status, harness install status, density/theme preferences

## ASCII wireframes

### Dashboard shell

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ sb  ⌘K                                              Sync ●  Search /         │
├──────────────┬───────────────────────────────────────────────────────────────┤
│ Chief of     │                                                               │
│ Staff        │                           content                              │
│  • Today     │                                                               │
│  • Tasks     │                                                               │
│  • Signals   │                                                               │
│  • Proposals │                                                               │
│  • Goals     │                                                               │
│  • Adapters  │                                                               │
│  • Settings  │                                                               │
│──────────────│                                                               │
│ Finance      │                                                               │
│ Health       │                                                               │
│ Reading      │                                                               │
│ Home         │                                                               │
└──────────────┴───────────────────────────────────────────────────────────────┘
```

### Today

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Today · Tue Sep 13                                  Plan today  Wrap today   │
├───────────────────────────────────┬──────────────────────────────────────────┤
│ Morning plan                      │ Evening wrap                             │
│ ┌───────────────────────────────┐ │ ┌──────────────────────────────────────┐ │
│ │ Top 3                         │ │ │ Completions                          │ │
│ │ 1. CXP-45827   91             │ │ │ • Closed backlog gap [signal:244]   │ │
│ │ 2. Review draft 84            │ │ │ • Updated changelog [signal:251]    │ │
│ │ 3. Triage bugs 79             │ │ └──────────────────────────────────────┘ │
│ └───────────────────────────────┘ │ ┌──────────────────────────────────────┐ │
│ ┌───────────────────────────────┐ │ │ Gap questions                        │ │
│ │ Time blocks / rationale       │ │ │ • Did ticket CXP-45831 move?        │ │
│ │ citations inline              │ │ │ • Missing evidence after 14:00      │ │
│ └───────────────────────────────┘ │ └──────────────────────────────────────┘ │
└───────────────────────────────────┴──────────────────────────────────────────┘
```

### Tasks

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Tasks                               [Domain v] [Source v] [Show score]      │
├──────────────────────────────────────────────────────────────────────────────┤
│ Score │ Task title                         Source  Domain   Energy   Status  │
│ 91    │ CXP-45827 Reduce backlog           jira    work     deep     open    │
│       │ goal: clear_jira_backlog · due now · complete ⏎                    │
│ 84    │ Draft wrap notes                   manual  work     shallow  open    │
│ 79    │ Review CHANGELOG proposal          changelog work   shallow  open    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Signals

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Signals                     [query____________] [Source] [Scope] [Date]      │
├───────────────────────────────┬───────────────────────────────────────────────┤
│ 14:22  git      feat: ranker  │ Title                                          │
│ 13:10  changelog Added wrap   │ Body preview                                   │
│ 10:03  jira     CXP-45827     │ raw_ref path#L42 / URL                         │
│ 09:17  tasks    Draft brief   │ refs: jira · repo · people                     │
└───────────────────────────────┴───────────────────────────────────────────────┘
```

### Proposals

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Proposals                                Pending 4                 A/R/S     │
├───────────────────────────────┬───────────────────────────────────────────────┤
│ #112 CHANGELOG pending        │ Exact payload                                 │
│ scope: ciq                    │ ## [2026-09-13]                               │
│ created 17:31                 │ - Fixed ranking bug in...                     │
│                               │ [Approve] [Reject] [Skip]                     │
├───────────────────────────────┼───────────────────────────────────────────────┤
│ #111 CHANGELOG approved       │ Detail / history                              │
└───────────────────────────────┴───────────────────────────────────────────────┘
```

### Goals

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Goals                                                   Alignment on         │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│ Contractual          │ Quarterly            │ Weekly                        │
│ Keep delivery trust  │ Reduce backlog       │ Keep queue under 10           │
│ linked tasks: 8      │ linked tasks: 5      │ linked tasks: 3               │
│ latest plan refs: 2  │ latest plan refs: 4  │ latest plan refs: 3           │
└──────────────────────┴──────────────────────┴───────────────────────────────┘
```

### Adapters

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Adapters                                              Sync all               │
├──────────────────────────────────────────────────────────────────────────────┤
│ changelog  ● ok     cursor: 2026-09-13T14:22Z   last sync 12s ago  Resync   │
│ git        ● ok     cursor: sha:8e68992         last sync 12s ago  Resync   │
│ jira       ● warn   token missing               last error auth     Setup    │
│ tasks      ● ok     cursor: task:981            last sync 12s ago  Resync   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Settings

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Settings                                                                     │
├───────────────────────────────┬───────────────────────────────────────────────┤
│ Identity                      │ Preferences                                   │
│ roots                         │ density: dense / comfortable                  │
│ goals file                    │ theme: dark / light / system                  │
│ harness install status        │ menu bar route enabled                        │
│ jira token: present/missing   │ PWA install help                              │
└───────────────────────────────┴───────────────────────────────────────────────┘
```

### Menu bar popover

```text
┌────────────────────────────────────┐
│ sb                    ● adapters ok│
├────────────────────────────────────┤
│ Top 3 today                        │
│ 91  CXP-45827 backlog cleanup   ›  │
│ 84  Draft wrap notes            ›  │
│ 79  Review proposal             ›  │
│                                    │
│ [Wrap now]                         │
│                                    │
│ ⌘K Open command palette            │
│ ↗ Open dashboard                   │
└────────────────────────────────────┘
```

## Why this structure works for later modules

The sidebar is intentionally an app registry, not a hardcoded chief-of-staff nav. That means:

- Finance can later add its own routes and palette actions.
- Health can add tracking views without touching chief-of-staff pages.
- Shared shell pieces — command palette, sidebar, top bar, preferences, theme, PWA install — stay reusable.

## Success criteria for the first scaffold

An engineer should be able to build a working v1 if the scaffold supports:

1. Connecting to the 15-tool MCP server over SSE.
2. Rendering Today, Tasks, Signals, Proposals, Goals, Adapters, and Settings.
3. Opening a global `⌘K` palette with direct tool-backed actions.
4. Handling optimistic updates for complete-task and approve-proposal.
5. Reusing the same app bundle for dashboard, menu bar view, and PWA install.
