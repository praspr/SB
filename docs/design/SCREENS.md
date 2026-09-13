# sb dashboard — Screens

Each screen below is described as a v1 build target. The chief-of-staff app owns the daily-operation views; Settings remains part of the same app but behaves more like a utility area.

---

## 1. Today

**Purpose**

Default landing view. It should answer: what matters now, what was planned, what got done, and what still needs wrap attention.

**Primary backend links**

- `get_day`
- `plan_day`
- `wrap_day`
- `standup`
- citation drill-ins via `search_signals`

**Key interactions**

- auto-load most recent day entry
- `Regenerate plan` button for morning use
- `Wrap today` button for evening use
- click citation chip to open signal-detail flyout

**Wireframe**

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Today · Tuesday, Sep 13                      Regenerate plan   Wrap today    │
├───────────────────────────────────┬──────────────────────────────────────────┤
│ Morning plan                      │ Evening wrap                             │
│ ┌───────────────────────────────┐ │ ┌──────────────────────────────────────┐ │
│ │ Top 3                         │ │ │ Completions                          │ │
│ │ 91 CXP-45827                  │ │ │ • Reduced backlog [signal:244]      │ │
│ │ 84 Draft wrap notes           │ │ │ • Updated ranker docs [signal:251]  │ │
│ │ 79 Review pending proposal    │ │ └──────────────────────────────────────┘ │
│ └───────────────────────────────┘ │ ┌──────────────────────────────────────┐ │
│ ┌───────────────────────────────┐ │ │ Gap questions                        │ │
│ │ Time blocks / rationale       │ │ │ • Did CXP-45831 move?               │ │
│ │ [signal:244] [signal:245]     │ │ │ • Missing afternoon evidence        │ │
│ └───────────────────────────────┘ │ └──────────────────────────────────────┘ │
└───────────────────────────────────┴──────────────────────────────────────────┘
```

---

## 2. Tasks

**Purpose**

Review and act on ranked planning units from JIRA, changelog, git, tasks-local, and manual entries.

**Primary backend links**

- `list_tasks`
- `get_task`
- `create_task`
- `complete_task`

**Key interactions**

- filter by domain and source
- inspect score rationale
- quick complete with optimistic feedback
- select a row to open a detail pane

**Wireframe**

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Tasks                            [All domains] [All sources] [+ New task]   │
├───────────────────────────────┬───────────────────────────────────────────────┤
│ 91  CXP-45827                 │ Task detail                                   │
│     jira · work · deep        │ score 91                                      │
│ 84  Draft wrap notes          │ rationale: high urgency + goal alignment      │
│     manual · work · shallow   │ linked signals: 244, 251                      │
│ 79  Review proposal           │ [Mark complete]                               │
└───────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 3. Signals

**Purpose**

Browse the evidence ledger, which is the source of truth for wrap citations and planning context.

**Primary backend links**

- `search_signals`
- `get_day`

**Key interactions**

- query search
- source, scope, date, and domain filtering
- click row to open full signal detail
- jump from signal to related task or wrap context later

**Wireframe**

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Signals               [query____________] [Source] [Scope] [Date] [Domain]  │
├───────────────────────────────┬───────────────────────────────────────────────┤
│ 14:22 git       feat: plan    │ full title                                    │
│ 13:10 changelog Added wrap    │ body                                           │
│ 10:03 jira      CXP-45827     │ raw_ref                                        │
│ 09:17 tasks     Draft notes   │ refs                                           │
└───────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 4. Proposals

**Purpose**

Handle the approval queue. This view exists because `sb` follows “propose, don’t act” for anything outside the local machine.

**Primary backend links**

- `list_proposals`
- `approve_proposal`
- `reject_proposal`

**Key interactions**

- select pending item
- inspect exact payload
- press `A` to approve, `R` to reject, `S` to skip
- optimistic status transition to keep batch review fast

**Wireframe**

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Proposals                                             Pending 4   A/R/S      │
├───────────────────────────────┬───────────────────────────────────────────────┤
│ #112 CHANGELOG pending        │ ## [2026-09-13]                               │
│ #111 CHANGELOG pending        │ - Fixed ranking bug in...                     │
│ #110 CHANGELOG approved       │                                               │
│                               │ [Approve] [Reject] [Skip]                     │
└───────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 5. Goals

**Purpose**

Make the tiered goals model visible and show how planning aligns with it. This is especially important because the ranker uses keyword alignment, so the UI should explain the link clearly.

**Primary backend links**

- `get_goals`
- `list_tasks`
- `get_day`

**Key interactions**

- scan tiers left to right
- select goal to inspect linked tasks and recent plan mentions
- identify drift when a goal has no recent alignment

**Wireframe**

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Goals                                                      Alignment          │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│ Contractual          │ Quarterly            │ Weekly                        │
│ Keep delivery trust  │ Reduce backlog       │ Queue under 10                │
│ 8 linked tasks       │ 5 linked tasks       │ 3 linked tasks                │
└──────────────────────┴──────────────────────┴───────────────────────────────┘
```

---

## 6. Adapters

**Purpose**

Show the health of each adapter, current cursor, last success, and failures. This is where the user understands why tasks or signals may be missing.

**Primary backend links**

- `sync_status`
- `sync_adapters`
- `get_roots`

**Key interactions**

- see green/amber/red state at a glance
- trigger one-click resync for any adapter
- inspect missing token/setup guidance

**Wireframe**

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Adapters                                                [Sync all]           │
├──────────────────────────────────────────────────────────────────────────────┤
│ changelog  ● ok    cursor 2026-09-13T14:22Z   last sync 12s ago   Resync    │
│ git        ● ok    cursor sha:8e68992         last sync 12s ago   Resync    │
│ jira       ● warn  token missing              last error auth     Setup      │
│ tasks      ● ok    cursor task:981            last sync 12s ago   Resync    │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Settings

**Purpose**

Utility area for local setup facts: identity, roots, goal file presence, secrets status, harness install status, density/theme preferences, and PWA help.

**Primary backend links**

- `whoami`
- `get_roots`
- `sync_status`

**Key interactions**

- inspect setup rather than edit rich forms in v1
- see whether `jira.token` is present
- verify Claude/OpenCode/Cursor/VS Code/launchd install status

**Wireframe**

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Settings                                                                     │
├───────────────────────────────┬───────────────────────────────────────────────┤
│ Identity / roots              │ Preferences                                   │
│ goals file                    │ density toggle                                │
│ secrets status                │ theme toggle                                  │
│ harness install status        │ install to Dock help                          │
└───────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 8. Menu bar quick view

**Purpose**

Ultra-compact glanceable surface for the top 3 tasks, one wrap action, and adapter health.

**Primary backend links**

- `list_tasks`
- `sync_status`
- `wrap_day`

**Key interactions**

- click a must-do to open or focus full dashboard with that task selected
- click `Wrap now`
- open full command palette in the main dashboard

**Wireframe**

```text
┌────────────────────────────────────┐
│ sb                    ● adapters ok│
├────────────────────────────────────┤
│ 91  CXP-45827 backlog cleanup   ›  │
│ 84  Draft wrap notes            ›  │
│ 79  Review proposal             ›  │
│                                    │
│ [Wrap now]                         │
│ ⌘K Open full palette               │
│ ↗ Open dashboard                   │
└────────────────────────────────────┘
```

---

## 9. Command palette

**Purpose**

Universal keyboard launcher for every high-frequency action exposed by the 15 MCP tools.

**Action groups**

- Rituals
- Sync
- Tasks
- Signals
- Proposals
- Navigation
- Settings

**Wireframe**

```text
┌────────────────────────────────────────────────────────────┐
│ > plan today                                              │
├────────────────────────────────────────────────────────────┤
│ Recent                                                     │
│   Wrap today                                      ⇧⌘W      │
│ Rituals                                                    │
│   Plan today                                      ⇧⌘P      │
│   Standup                                         ⇧⌘S      │
│ Sync                                                       │
│   Sync all                                        ⇧⌘R      │
│ Navigation                                                 │
│   Go to Proposals                                  G then P│
└────────────────────────────────────────────────────────────┘
```

---

## 10. PWA install experience

**Purpose**

Make the dashboard easy to install to the Dock with standalone display mode and no browser chrome.

**Flow**

1. Settings shows “Install to Dock” guidance.
2. If install is available, show one clear CTA.
3. After install, the app launches directly into `/today` in standalone mode.

**Wireframe**

```text
┌────────────────────────────────────────────────────────────┐
│ Install sb to Dock                                         │
│ Local dashboard, standalone window, no browser chrome.     │
│                                                            │
│ [Install now]                                              │
│                                                            │
│ If Safari hides the prompt: Share → Add to Dock            │
└────────────────────────────────────────────────────────────┘
```
