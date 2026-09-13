# sb dashboard — Implementation Plan

## Recommended stack

| Layer | Choice | Why |
|---|---|---|
| Bundler | Vite | fast local iteration for a localhost-only app |
| UI | React 18 + TypeScript | requested stack, predictable component model |
| Styling | Tailwind CSS | fast path to a dense, polished Linear-like UI |
| Primitives | shadcn/ui | accessible inputs, dialogs, popovers, command shell base |
| Data | `@tanstack/react-query` | ideal for MCP-backed caching and invalidation |
| Routing | `@tanstack/react-router` | route-level loaders, typed search params, good shell ergonomics |
| Local UI state | `zustand` | lightweight state for palette, selection, density, theme |
| Palette | `cmdk` | proven `⌘K` experience |
| Motion | `framer-motion` | practical palette spring + view transitions |
| PWA | `vite-plugin-pwa` | manifest + icons + standalone setup |

## Scope guardrails

- Build a React scaffold only.
- Do not reimplement ranking, planning, wrap logic, or adapter logic in the client.
- Treat the Python MCP server as the source of truth.
- No persistent chat UI.
- No extra backend endpoints are required for v1 if the MCP transport layer is implemented cleanly.

## MCP integration notes

The app connects to:

- `http://127.0.0.1:8787/sse`

The backend exposes 15 tools:

| Group | Tools |
|---|---|
| State | `list_tasks`, `get_task`, `create_task`, `complete_task` |
| Rituals | `plan_day`, `wrap_day`, `standup` |
| Evidence | `search_signals`, `get_day` |
| Sync | `sync_adapters`, `sync_status` |
| Proposals | `list_proposals`, `approve_proposal`, `reject_proposal` |
| Context | `get_goals`, `get_roots`, `whoami` |

### Frontend transport shape

Create a small MCP client layer that exposes:

```ts
callTool<TParams, TResult>(name: string, params?: TParams): Promise<TResult>
subscribe(onEvent: (event: McpEvent) => void): () => void
```

Responsibilities:

- maintain the SSE session
- marshal JSON-RPC/MCP messages
- handle request ids and errors
- normalize tool errors into UI-friendly exceptions
- keep an event channel open for future live invalidation

### Query mapping

| Screen | Query hooks |
|---|---|
| Today | `useToday`, `useSyncStatus` |
| Tasks | `useTasks`, `useCompleteTask` |
| Signals | `useSignals` |
| Proposals | `useProposals`, `useApproveProposal`, `useRejectProposal` |
| Goals | `useGoals`, `useTasks` |
| Adapters | `useSyncStatus`, `useSyncAdapters`, `useRoots` |
| Settings | `useWhoAmI`, `useRoots`, `useSyncStatus` |

## Mutation behavior

### Optimistic updates required

1. **Task complete**
   - mark row completed immediately
   - dim row and update counts
   - rollback on error

2. **Proposal approve / reject**
   - update status immediately
   - fade row from pending queue
   - rollback on error

### Non-optimistic but animated

- `plan_day`
- `wrap_day`
- `standup`
- `sync_adapters`

These should show skeletons or progress states because they may take longer and produce broader data changes.

## Phase build order

## Phase A — shell + Today

Goal: first usable dashboard loop.

Build:

- app bootstrap
- tokens + theme + density support
- `AppShell`, `Sidebar`, `TopBar`, `CommandPalette`
- module registry with Chief of Staff module only
- Today route
- `useToday`, `usePlanDay`, `useWrapDay`, `useStandup`, `useSyncStatus`
- citation flyout stub wired from `[signal:N]`

Acceptance:

- `/today` loads current day data
- `Plan today` works through MCP and refreshes the screen
- `Wrap today` works through MCP and shows completions/gap questions
- `⌘K` opens and can run Plan/Wrap/Standup/Navigation actions

## Phase B — Tasks + Signals

Goal: make `sb` operational for ranking and evidence browsing.

Build:

- Tasks route with filters, detail pane, quick complete
- Signals route with query/filter bar and detail flyout
- `useTasks`, `useCompleteTask`, `useSignals`
- menu-bar route can already reuse top-3 tasks

Acceptance:

- tasks can be filtered by domain/source
- complete action is optimistic
- signals can be searched and filtered
- clicking a citation opens the corresponding signal detail

## Phase C — Proposals + Goals + Settings

Goal: expose approval queue, alignment model, and local setup context.

Build:

- Proposals route with keyboard approve/reject/skip
- Goals route with tier columns and alignment lists
- Settings route with identity, roots, secrets status, harness status, preferences
- `useProposals`, `useApproveProposal`, `useRejectProposal`, `useGoals`, `useWhoAmI`, `useRoots`

Acceptance:

- pending proposals can be reviewed from exact payload text
- `A` approves selected proposal with optimistic feedback
- goals display contractual/quarterly/weekly tiers
- settings shows whether JIRA is blocked by missing token

## Phase D — menu bar + PWA

Goal: finish the three required form factors.

Build:

- `/menu` compact route with 360px layout
- menu-bar handoff state so clicking a task opens `/tasks?taskId=...`
- PWA manifest, icons, standalone mode, install help route
- browser/PWA chrome adjustments for standalone feel

Acceptance:

- menu route renders top 3 must-dos + adapter health + Wrap now
- clicking a must-do navigates to the full dashboard with selection preserved
- app is installable via Add to Dock
- standalone mode hides browser framing cleanly

## Command palette action spec

Each palette item should show:

- title
- group
- keyboard shortcut
- optional subtitle
- side effect target

Minimum v1 actions:

| Group | Action | MCP tool |
|---|---|---|
| Rituals | Plan today | `plan_day` |
| Rituals | Wrap today | `wrap_day` |
| Rituals | Standup | `standup` |
| Sync | Sync all | `sync_adapters` |
| Sync | Sync changelog | `sync_adapters(adapter='changelog')` |
| Sync | Sync git | `sync_adapters(adapter='git')` |
| Sync | Sync jira | `sync_adapters(adapter='jira')` |
| Sync | Sync tasks | `sync_adapters(adapter='tasks')` |
| Tasks | New task | `create_task` |
| Tasks | Mark selected done | `complete_task` |
| Tasks | Find task | `list_tasks` |
| Signals | Search signals | `search_signals` |
| Proposals | Approve next pending | `approve_proposal` |
| Proposals | Reject next pending | `reject_proposal` |
| Navigation | Go to Today/Tasks/Signals/Proposals/Goals/Adapters/Settings | route only |
| Settings | Open config/setup | route only |

## Error handling

### App-wide conditions

- **MCP server unreachable** — show a full-panel reconnect state with endpoint string and “Check `sb mcp serve` / launchd” guidance
- **JIRA token missing** — surface as adapter warning, not app failure
- **No goals file** — non-blocking empty state on Goals screen
- **No signals yet** — suggest running Sync all

## Settings scope for the first scaffold

To stay aligned with the current backend, the first scaffold should split Settings into:

### Build now from existing MCP tools

- identity card from `whoami`
- roots summary from `get_roots`
- adapter state from `sync_status`
- inferred JIRA secret status from adapter health
- appearance preferences stored client-side

### Mark as follow-on backend support

- full config editor
- explicit Keychain secret list/manage flows
- harness install status detection for Claude/OpenCode/Cursor/VS Code/launchd

If `@fixer` wants these in the first implementation pass, the clean path is to add small new MCP tools rather than bypassing the backend contract.

### Copy style

Keep copy direct and operational:

- “No signals matched this filter.”
- “JIRA is configured but unavailable.”
- “Proposal approved. Waiting for backend confirmation…”

## Handoff notes for `@fixer`

If this spec is handed to `@fixer`, the scaffold should start with these priorities:

1. Build the shell and route tree exactly once.
2. Implement the MCP client before building many screens.
3. Keep hooks thin and typed to tool outputs.
4. Reuse one component set across dashboard, menu-bar, and PWA.
5. Do not add free-form chat; invest effort in command palette, split views, and evidence flyouts.
