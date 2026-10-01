import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useToast } from '@/lib/useToast'

describe('useToast', () => {
  beforeEach(() => {
    useToast.getState().clear()
    vi.useFakeTimers()
  })

  it('queues and auto-dismisses by kind timeout', () => {
    useToast.getState().show({ kind: 'success', message: 'Saved' })
    expect(useToast.getState().queue).toHaveLength(1)
    vi.advanceTimersByTime(3000)
    expect(useToast.getState().queue).toHaveLength(0)
  })

  it('supports manual dismiss', () => {
    const id = useToast.getState().show({ kind: 'error', message: 'Failed' })
    useToast.getState().dismiss(id)
    expect(useToast.getState().queue).toEqual([])
  })
})
