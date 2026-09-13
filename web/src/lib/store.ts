import { create } from 'zustand'

type UiState = {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  commandPaletteOpen: boolean
  setCommandPaletteOpen: (open: boolean) => void
  addTodoOpen: boolean
  setAddTodoOpen: (open: boolean) => void
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
  setAddTodoOpen: (open) => set({ addTodoOpen: open }),
  focusQuickAddSignal: 0,
  triggerFocusQuickAdd: () => set((s) => ({ focusQuickAddSignal: s.focusQuickAddSignal + 1 })),
}))
