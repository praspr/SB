# sb dashboard — Components

This list covers the core v1 scaffold. Components are intentionally mapped to the backend object model and the required surfaces.

## Shell components

### 1. `AppShell`

Owns the full desktop frame: sidebar, top bar, main content, overlay hosts, and density/theme classes. It switches between dashboard and menu-bar layout profiles without changing the data layer.

```ts
type AppShellProps = {
  surface: 'dashboard' | 'menu'
  activeModuleId: string
  children: React.ReactNode
}
```

### 2. `Sidebar`

Renders the module registry and the current module's nav items. It keeps future apps visible as first-class shell citizens instead of hiding them behind feature flags.

```ts
type SidebarProps = {
  modules: SbModule[]
  activeModuleId: string
  activePath: string
}
```

### 3. `SidebarAppSwitcher`

Shows app-level entries such as Chief of Staff, Finance, Health, Reading, and Home. In v1 only Chief of Staff is active, but the control is already designed to scale.

```ts
type SidebarAppSwitcherProps = {
  modules: Pick<SbModule, 'id' | 'label' | 'icon' | 'defaultRoute'>[]
  activeModuleId: string
}
```

### 4. `TopBar`

Provides route title, global search affordance, sync status summary, and command palette trigger. It should always show `⌘K` and current adapter health because both are cross-app shell concerns.

```ts
type TopBarProps = {
  title: string
  subtitle?: string
  adapterHealth: 'ok' | 'warn' | 'error'
  onOpenPalette: () => void
}
```

### 5. `CommandPalette`

Global `cmdk`-based action launcher with grouped results, recent actions, shortcuts, and fuzzy matching. This is the main control plane for rituals, sync, navigation, and task actions.

```ts
type CommandPaletteProps = {
  open: boolean
  actions: PaletteAction[]
  recentActionIds: string[]
  onOpenChange: (open: boolean) => void
}
```

## Today components

### 6. `TodayView`

Composes the Today route: hero strip, primary actions, plan column, wrap column, and optional standup block. It expects already-fetched day data and keeps the layout stable while child sections refresh.

```ts
type TodayViewProps = {
  dateLabel: string
  plan?: DailyEntryPlan
  wrap?: DailyEntryWrap
  isLoading: boolean
}
```

### 7. `TodayHero`

Compact top section for current day, last sync, and ritual actions: Plan today, Wrap today, Standup, Sync all. It creates the "open and act immediately" behavior required by the morning ritual flow.

```ts
type TodayHeroProps = {
  dateLabel: string
  lastUpdated?: string
  onPlan: () => void
  onWrap: () => void
  onStandup: () => void
  onSync: () => void
}
```

### 8. `PlanPanel`

Shows the latest morning plan: top tasks, score rationale, time blocks, and citations. It is optimized for scanning rather than editing.

```ts
type PlanPanelProps = {
  items: PlanItem[]
  rationaleMd?: string
  citations: Citation[]
  onCitationClick: (signalId: number) => void
}
```

### 9. `WrapPanel`

Shows the wrap result in two sub-sections: completions and gap questions. This directly matches the required storyboard and makes `[signal:N]` citations first-class.

```ts
type WrapPanelProps = {
  completions: WrapCompletion[]
  gapQuestions: string[]
  citations: Citation[]
  onCitationClick: (signalId: number) => void
}
```

### 10. `DailyEntryCard`

Reusable card for any dated plan/wrap/standup block. Useful in Today and later in historical day browsing.

```ts
type DailyEntryCardProps = {
  title: string
  status?: 'current' | 'stale' | 'missing'
  actions?: React.ReactNode
  children: React.ReactNode
}
```

## Tasks components

### 11. `TaskList`

Ranked task list with filter bar, keyboard selection, and empty state support. It should handle dense list rendering cleanly because tasks are a high-frequency surface.

```ts
type TaskListProps = {
  tasks: Task[]
  selectedTaskId?: string
  isLoading: boolean
  filters: TaskFilters
  onSelect: (taskId: string) => void
}
```

### 12. `TaskRow`

Single ranked task row showing title, score, source, domain, energy, due state, and complete action. It should support optimistic completion and a selected state for keyboard workflows.

```ts
type TaskRowProps = {
  task: Task
  selected?: boolean
  onSelect: () => void
  onComplete: () => void
}
```

### 13. `ScoreBar`

Small visual breakdown of task score with weighted segments or a single fill meter. It makes the ranker's output legible without turning the list into a spreadsheet.

```ts
type ScoreBarProps = {
  value: number
  parts?: Array<{ label: string; value: number }>
}
```

### 14. `TaskDetailPane`

Right-side detail panel for the selected task, with source reference, rationale, goal alignment, and quick actions. It avoids overloading the row itself.

```ts
type TaskDetailPaneProps = {
  task?: Task
  relatedSignals?: Signal[]
  onComplete?: () => void
}
```

## Signals components

### 15. `SignalTimeline`

Scrollable evidence list with time grouping and filters. It is designed around `Signal` as the system-of-record object.

```ts
type SignalTimelineProps = {
  signals: Signal[]
  selectedSignalId?: number
  onSelect: (signalId: number) => void
}
```

### 16. `SignalTimelineItem`

Condensed row showing source, time, title, scope, and raw reference hint. It needs to stay scannable even when signal counts grow large.

```ts
type SignalTimelineItemProps = {
  signal: Signal
  selected?: boolean
  onClick: () => void
}
```

### 17. `SignalDetailFlyout`

Overlay or side flyout that shows the complete signal body, refs, `raw_ref`, and any linked task or proposal context. This is the endpoint for clicking a `[signal:N]` citation anywhere in the app.

```ts
type SignalDetailFlyoutProps = {
  signal?: Signal
  open: boolean
  onOpenChange: (open: boolean) => void
}
```

### 18. `CitationChip`

Compact interactive chip for evidence references such as `[signal:244]`. Must use tabular numerals and feel like a link, not a decorative badge.

```ts
type CitationChipProps = {
  signalId: number
  onClick: (signalId: number) => void
}
```

## Proposals components

### 19. `ProposalList`

Master list for the approval queue, grouped by status or filtered to pending. It should support keyboard movement and keep the selected proposal in sync with the detail pane.

```ts
type ProposalListProps = {
  proposals: Proposal[]
  selectedProposalId?: number
  onSelect: (proposalId: number) => void
}
```

### 20. `ProposalCard`

Compact proposal row showing id, type, scope, created time, and status. It should clearly surface when an action is still pending versus already approved or rejected.

```ts
type ProposalCardProps = {
  proposal: Proposal
  selected?: boolean
  onSelect: () => void
}
```

### 21. `ProposalPayloadPanel`

Exact payload viewer with monospace block styling, action buttons, and shortcut hints. This is where the user validates the precise outgoing CHANGELOG or future remote action content.

```ts
type ProposalPayloadPanelProps = {
  proposal?: Proposal
  onApprove: () => void
  onReject: () => void
  onSkip: () => void
}
```

## Goals components

### 22. `GoalTierColumn`

Column component for contractual, quarterly, or weekly goals. It renders goal title, weight, linked tasks, and recent plan references.

```ts
type GoalTierColumnProps = {
  tier: 'contractual' | 'quarterly' | 'weekly'
  goals: Goal[]
  onSelectGoal?: (goalId: string) => void
}
```

### 23. `GoalAlignmentList`

Shows tasks or plan items linked to a selected goal, making the keyword-based ranker transparent rather than opaque.

```ts
type GoalAlignmentListProps = {
  goal: Goal
  linkedTasks: Task[]
  linkedDayEntries?: DailyEntry[]
}
```

## Adapters and settings components

### 24. `AdapterStatusTable`

Operational table for adapter health, cursor, last sync time, last error, and re-sync actions. It turns backend sync state into an admin-quality UI instead of a plain list.

```ts
type AdapterStatusTableProps = {
  adapters: SyncState[]
  onResync: (adapter?: string) => void
}
```

### 25. `AdapterStatusPill`

Small semantic status indicator used in the top bar, menu bar, and adapter rows. Must always pair color with text label.

```ts
type AdapterStatusPillProps = {
  status: 'ok' | 'warn' | 'error'
  label?: string
}
```

### 26. `SettingsSection`

Generic settings layout block for identity, roots, secrets, harnesses, and local appearance preferences. Helps keep the utility page readable.

```ts
type SettingsSectionProps = {
  title: string
  description?: string
  children: React.ReactNode
}
```

### 27. `SecretsStatusCard`

Read-only summary of secret presence, especially `jira.token`, with guidance on what command to run when missing. Since the backend stores secrets in Keychain, the UI should report presence, not values.

```ts
type SecretsStatusCardProps = {
  items: Array<{ key: string; present: boolean; hint?: string }>
}
```

### 28. `HarnessStatusCard`

Shows whether Claude Code, OpenCode, Cursor, VS Code, and launchd have been installed and detected. This matches the existing `sb install --all` backend fact.

```ts
type HarnessStatusCardProps = {
  harnesses: Array<{ name: string; installed: boolean; detail?: string }>
}
```

## Shared utility components

### 29. `EmptyState`

Purpose-built empty state with icon, short explanation, and one next action. Every major list in `sb` needs a useful empty state because missing data often means “not synced yet,” not “nothing exists.”

```ts
type EmptyStateProps = {
  title: string
  body: string
  actionLabel?: string
  onAction?: () => void
}
```

### 30. `SkeletonRow`

Layout-matched skeleton block for rows, cards, and split panels. It should mirror the final component dimensions so route loads do not shift content.

```ts
type SkeletonRowProps = {
  lines?: number
  compact?: boolean
}
```
