import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({ callTool: vi.fn() }))

describe('schedules client', () => {
  beforeEach(() => vi.resetModules())

  it('calls scheduler tools', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([])
    const api = await import('./schedules')
    await api.listScheduledRituals()
    await api.deleteScheduledRitual(2)
    expect(callTool).toHaveBeenCalledWith('list_scheduled_rituals')
    expect(callTool).toHaveBeenCalledWith('delete_scheduled_ritual', { id: 2 })
  })
})
