import { create } from 'zustand'

export type TodoDraft = {
  title?: string
  description?: string
  priority?: 1 | 2 | 3 | 4
  external_source?: string
  external_ref?: string
  jira_ref?: string
}

type UiState = {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
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
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  addTodoOpen: false,
  todoDraft: null,
  setAddTodoOpen: (open) => set({ addTodoOpen: open, ...(!open ? { todoDraft: null } : {}) }),
  openAddTodo: (draft = {}) => set({ addTodoOpen: true, todoDraft: draft }),
  focusQuickAddSignal: 0,
  triggerFocusQuickAdd: () => set((s) => ({ focusQuickAddSignal: s.focusQuickAddSignal + 1 })),
}))
