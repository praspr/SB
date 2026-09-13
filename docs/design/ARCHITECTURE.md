# sb dashboard — Architecture

## App shape

The frontend should be a single React app with one shared shell and multiple display profiles:

- **Dashboard profile** — full-width browser/PWA app
- **Menu profile** — 360px quick view route using the same data layer
- **Standalone PWA profile** — same dashboard routes, different install/display metadata

The app should stay thin. The Python `sb` backend already owns ingestion, ranking, planning, wrap generation, proposal execution, and sync logic. The React app should primarily:

- call MCP tools
- cache and normalize responses
- manage view state
- provide fast keyboard and list/detail flows

One practical constraint: the current MCP tool surface is strong for daily operations, but thinner for settings administration. A working v1 scaffold should treat **Settings** as two layers:

- **MCP-backed now** — identity, roots, goals presence, adapter health, JIRA blocked/unblocked status
- **Needs follow-on support** — true config editing, secret mutation, harness install inspection from the browser

That keeps the initial build honest to the existing 15-tool backend while leaving a clear path for small follow-up MCP additions.

## Recommended stack

- Vite
- React 18
- TypeScript
- Tailwind CSS
- shadcn/ui for primitives
- `@tanstack/react-query` for data fetching and mutation state
- `@tanstack/react-router` for route-driven layouts and search params
- `zustand` for local UI state only
- `cmdk` for the command palette
- `framer-motion` for view transitions and palette open/close motion
- `vite-plugin-pwa` for manifest/service worker generation

## Folder layout

```text
src/
  app/
    providers/
      QueryProvider.tsx
      ThemeProvider.tsx
      CommandProvider.tsx
    router.tsx
    registry.ts
  components/
    shell/
      AppShell.tsx
      Sidebar.tsx
      SidebarAppSwitcher.tsx
      TopBar.tsx
      CommandPalette.tsx
    today/
      TodayHero.tsx
      PlanPanel.tsx
      WrapPanel.tsx
      DailyEntryCard.tsx
    tasks/
      TaskList.tsx
      TaskRow.tsx
      ScoreBar.tsx
    signals/
      SignalTimeline.tsx
      SignalTimelineItem.tsx
      SignalDetailFlyout.tsx
      CitationChip.tsx
    proposals/
      ProposalList.tsx
      ProposalCard.tsx
      ProposalPayloadPanel.tsx
    goals/
      GoalTierColumn.tsx
      GoalAlignmentList.tsx
    adapters/
      AdapterStatusTable.tsx
      AdapterStatusPill.tsx
    settings/
      SettingsSection.tsx
      SecretsStatusCard.tsx
      HarnessStatusCard.tsx
    shared/
      EmptyState.tsx
      FilterBar.tsx
      SearchField.tsx
      SegmentedControl.tsx
      SkeletonRow.tsx
      Flyout.tsx
      Kbd.tsx
  hooks/
    query/
      useToday.ts
      useTasks.ts
      useSignals.ts
      useProposals.ts
      useGoals.ts
      useSyncStatus.ts
      useRoots.ts
      useWhoAmI.ts
    mutations/
      usePlanDay.ts
      useWrapDay.ts
      useStandup.ts
      useCompleteTask.ts
      useApproveProposal.ts
      useRejectProposal.ts
      useSyncAdapters.ts
    ui/
      useCommandShortcuts.ts
      useDensity.ts
      useSelectedTask.ts
  lib/
    mcp/
      client.ts
      sseTransport.ts
      toolNames.ts
      notifications.ts
      types.ts
    query/
      keys.ts
      invalidation.ts
    formatting/
      dates.ts
      scores.ts
      citations.ts
      status.ts
    module/
      types.ts
      commands.ts
  modules/
    chief-of-staff/
      index.ts
      routes/
        today.tsx
        tasks.tsx
        signals.tsx
        proposals.tsx
        goals.tsx
        adapters.tsx
        settings.tsx
      commands.ts
      navigation.ts
  pages/
    menu/
      MenuBarView.tsx
    install/
      PwaInstallHelp.tsx
  styles/
    globals.css
    tokens.css
  main.tsx
```

## Routing

### Top-level routes

```text
/
  /today
  /tasks
  /signals
  /proposals
  /goals
  /adapters
  /settings
  /menu              # 360px quick view surface
  /install           # PWA install guidance / fallback page
```

### Route model

- Chief of Staff is registered as the default app and owns the routes above.
- Future apps mount under app-specific roots:
  - `/finance/*`
  - `/health/*`
  - `/reading/*`
  - `/home/*`

### Search param strategy

Use URL search params for all view filters so the app feels linkable and stateful:

- `/tasks?domain=work&source=jira`
- `/signals?query=wrap&source=git&since=2026-09-01`
- `/proposals?status=pending`
- `/goals?tier=weekly`

## Data flow

## 1. MCP transport layer

The frontend should talk only to `http://127.0.0.1:8787/sse`.

Transport responsibilities:

- open a long-lived SSE connection
- issue MCP/JSON-RPC tool calls over the expected transport contract
- handle request/response correlation
- listen for server notifications and lifecycle events
- expose a typed `callTool(name, params)` API to the rest of the app

## 2. Query layer

Each backend object family gets a focused React Query hook:

| Hook | Primary MCP tool(s) |
|---|---|
| `useToday(date?)` | `get_day`, `plan_day`, `wrap_day`, `standup` |
| `useTasks(filters)` | `list_tasks`, `get_task` |
| `useSignals(filters)` | `search_signals` |
| `useProposals(status)` | `list_proposals` |
| `useGoals(activeOnly)` | `get_goals` |
| `useSyncStatus()` | `sync_status` |
| `useRoots()` | `get_roots` |
| `useWhoAmI()` | `whoami` |

Query keys should follow object shape, not screen shape:

```ts
['today', date]
['tasks', filters]
['task', taskId]
['signals', filters]
['proposals', status]
['goals', activeOnly]
['sync-status']
['roots']
['whoami']
```

## 3. Mutation layer

Mutations should be narrow and invalidation-aware:

- `usePlanDay()` → invalidates `['today', date]`, `['tasks', *]`
- `useWrapDay()` → invalidates `['today', date]`, `['proposals', *]`, `['signals', *]`
- `useStandup()` → invalidates `['today', date]`
- `useCompleteTask()` → optimistic update for task row + list count
- `useApproveProposal()` → optimistic status transition for selected proposal
- `useRejectProposal()` → optimistic removal from pending queue
- `useSyncAdapters()` → invalidates `['sync-status']`, `['signals', *]`, `['tasks', *]`

## 4. Live updates

Use the SSE connection for live invalidation whenever the MCP server emits completion or status notifications.

Suggested behavior:

- after `sync_adapters`, invalidate tasks, signals, and sync status
- after `plan_day` or `wrap_day`, invalidate the current day entry
- if the server later adds push notifications for adapter completion or proposal execution, route those directly into query invalidation

If the server currently emits no useful push notifications beyond transport keepalives, keep the SSE connection open for future compatibility and rely on mutation-driven invalidation in v1.

## Loading and empty states

- Skeletons should match final layout dimensions to avoid layout shift.
- Each major list gets a purpose-built empty state.

Examples:

- **Tasks empty:** “No ranked tasks yet. Run Sync all or create a manual task.”
- **Signals empty:** “No evidence matched. Broaden date range or sync adapters.”
- **Proposals empty:** “Approval queue is clear. Wrap day will create CHANGELOG proposals when needed.”
- **Goals empty:** “No goals loaded. Add `~/.config/sb/goals.yaml` to unlock alignment.”
- **Adapters error:** “JIRA token missing. Store `jira.token` in Keychain to enable this adapter.”

## Module registry contract

The shell should never hardcode app navigation. It should consume registered modules.

```ts
import type { ReactNode, ComponentType } from 'react'

export type PaletteAction = {
  id: string
  title: string
  subtitle?: string
  group: 'Rituals' | 'Sync' | 'Tasks' | 'Signals' | 'Proposals' | 'Navigation' | 'Settings' | string
  shortcut?: string[]
  keywords?: string[]
  perform: () => Promise<void> | void
}

export type ModuleRoute = {
  path: string
  label: string
  icon: ComponentType<{ className?: string }>
  element: ReactNode
  commandId?: string
}

export type ModuleNavItem = {
  id: string
  label: string
  icon: ComponentType<{ className?: string }>
  to: string
  badgeCountQueryKey?: unknown[]
}

export interface SbModule {
  id: string
  label: string
  icon: ComponentType<{ className?: string }>
  order: number
  defaultRoute: string
  navItems: ModuleNavItem[]
  routes: ModuleRoute[]
  useBootData?: () => {
    isLoading: boolean
    hasError: boolean
  }
  getPaletteActions?: () => PaletteAction[]
}
```

### Chief-of-Staff module responsibilities

The v1 Chief-of-Staff module should contribute:

- sidebar icon and label
- seven routes: Today, Tasks, Signals, Proposals, Goals, Adapters, Settings
- command palette actions backed by the 15 existing MCP tools
- optional boot data hook that preloads `whoami`, `sync_status`, and the current day entry

## Command palette architecture

Use `cmdk` with three inputs:

1. static shell actions
2. module-contributed actions
3. recent-action history from local storage

Action groups for v1:

- **Rituals** — Plan today, Wrap today, Standup
- **Sync** — Sync all, Sync changelog, Sync git, Sync jira, Sync tasks
- **Tasks** — New task, Mark selected task done, Find task
- **Signals** — Search signals
- **Proposals** — Approve next pending, Reject next pending
- **Navigation** — Go to Today/Tasks/Signals/Proposals/Goals/Adapters/Settings
- **Settings** — Open settings, open secrets status, open harness status

## State ownership

### React Query owns server state

- day data
- tasks
- signals
- proposals
- goals
- sync status
- roots
- identity

### Zustand owns local UI state

- command palette open/closed
- selected module
- selected task / selected proposal / selected signal
- density preference
- theme preference
- menu-bar handoff target

Do not duplicate MCP data inside Zustand.

## Menu bar surface

Because this phase is a React localhost app, the menu-bar UI should be treated as a **special route and layout profile**, not a second app.

Recommended route:

- `/menu`

Behavior:

- fixed 360px layout
- reads top 3 tasks from the same `list_tasks` query
- exposes `Wrap now`
- clicking a task navigates to `/today?taskId=...` or `/tasks?taskId=...`

This gives a later native menu-bar wrapper a stable URL to host.

## Settings integration boundary

Because the browser cannot directly inspect Keychain, launchd, or arbitrary filesystem state in a safe way, the full Settings vision should be staged:

### Works with the current MCP surface

- identity summary from `whoami`
- roots from `get_roots`
- adapter health from `sync_status`
- inferred JIRA secret health from the JIRA adapter state
- local UI preferences like density/theme stored in browser state

### Requires small backend follow-up

- config file read/write helper
- secret presence/list helper
- harness install status helper

If those helpers are added later, they should follow the same MCP pattern instead of introducing a separate frontend-only data path.

## PWA setup notes

Required assets and settings:

- manifest with app name: `sb`
- short name: `sb`
- display: `standalone`
- theme/background colors from dark theme tokens
- maskable icons sized for macOS dock install
- install prompt affordance in Settings and `/install`

Recommended manifest shape:

```json
{
  "name": "sb",
  "short_name": "sb",
  "start_url": "/today",
  "display": "standalone",
  "background_color": "#0C111B",
  "theme_color": "#0F1727",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

### Service worker posture

Keep it conservative.

- cache shell assets for fast relaunch
- do not aggressively cache MCP responses
- treat data as live and local
- if offline, render the last successful shell and show “sb server unavailable” for data panels

## Accessibility and keyboard rules

- full keyboard navigation for sidebar, lists, palette, and proposal actions
- visible focus rings using the accent color
- tabular numerals for scores, signal IDs, and timestamps
- no information conveyed by color alone; pair dots with text labels

## Engineering guardrails

- Keep all domain logic in the backend.
- Keep the frontend typed directly against MCP response shapes.
- Prefer route state and query state over hidden component state.
- Make menu bar and PWA reuse the same components wherever possible.
