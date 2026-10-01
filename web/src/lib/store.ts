import { create } from 'zustand'
import type { Task } from './mock-data'

export type TodoDraft = {
  title?: string
  description?: string
  priority?: 1 | 2 | 3 | 4
  external_source?: string
  external_ref?: string
  jira_ref?: string
  goal_id?: number | null
  recurrence_rule?: string | null
  edit?: Task
}

type UiState = {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  settingsOpen: boolean
  setSettingsOpen: (open: boolean) => void
  settingsTab: 'connections' | 'schedules' | 'projects' | 'sessions' | 'diagnostics'
  setSettingsTab: (tab: UiState['settingsTab']) => void
  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void
  addTodoOpen: boolean
  todoDraft: TodoDraft | null
  setAddTodoOpen: (open: boolean) => void
  openAddTodo: (draft?: TodoDraft) => void
  focusQuickAddSignal: number
  triggerFocusQuickAdd: () => void
}

export const useUiStore = create<UiState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  settingsOpen: false,
  setSettingsOpen: (open) => set({ settingsOpen: open }),
  settingsTab: 'connections',
  setSettingsTab: (tab) => set({ settingsTab: tab }),
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  addTodoOpen: false,
  todoDraft: null,
  setAddTodoOpen: (open) => set({ addTodoOpen: open, ...(!open ? { todoDraft: null } : {}) }),
  openAddTodo: (draft = {}) => set({ addTodoOpen: true, todoDraft: draft }),
  focusQuickAddSignal: 0,
  triggerFocusQuickAdd: () => set((s) => ({ focusQuickAddSignal: s.focusQuickAddSignal + 1 })),
}))
