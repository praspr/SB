import { create } from 'zustand'

export type ToastKind = 'success' | 'error' | 'info'

export type ToastItem = {
  id: number
  kind: ToastKind
  message: string
  timeout_ms: number
}

type ToastInput = {
  kind: ToastKind
  message: string
  timeout_ms?: number
}

type ToastState = {
  queue: ToastItem[]
  show: (input: ToastInput) => number
  dismiss: (id: number) => void
  clear: () => void
}

const nextTimeoutForKind: Record<ToastKind, number> = {
  success: 3000,
  error: 6000,
  info: 4000,
}

let nextId = 1
const timers = new Map<number, number>()

function scheduleTimer(callback: () => void, timeout: number): number | null {
  if (typeof globalThis.setTimeout !== 'function') return null
  return globalThis.setTimeout(callback, timeout) as unknown as number
}

function clearScheduledTimer(id: number) {
  if (typeof globalThis.clearTimeout !== 'function') return
  globalThis.clearTimeout(id)
}

export const useToast = create<ToastState>((set, get) => ({
  queue: [],
  show: (input) => {
    const id = nextId++
    const timeout_ms = input.timeout_ms ?? nextTimeoutForKind[input.kind]
    set((state) => ({
      queue: [...state.queue, { id, kind: input.kind, message: input.message, timeout_ms }],
    }))

    const timer = scheduleTimer(() => {
        get().dismiss(id)
      }, timeout_ms)
    if (timer != null) {
      timers.set(id, timer)
    }

    return id
  },
  dismiss: (id) => {
    const timer = timers.get(id)
    if (timer) {
      clearScheduledTimer(timer)
      timers.delete(id)
    }
    set((state) => ({ queue: state.queue.filter((item) => item.id !== id) }))
  },
  clear: () => {
    timers.forEach((timer) => clearScheduledTimer(timer))
    timers.clear()
    set({ queue: [] })
  },
}))
