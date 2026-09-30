import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({ callTool: vi.fn() }))

describe('goals client', () => {
  beforeEach(() => vi.resetModules())

  it('calls goal tools with typed payloads', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([])
    const api = await import('./goals')
    await api.listGoalsV2({ tier: 'weekly', status: 'active' })
    await api.getGoalV2(7)
    await api.heatmapLastWeek()
    expect(callTool).toHaveBeenCalledWith('list_goals_v2', { tier: 'weekly', status: 'active' })
    expect(callTool).toHaveBeenCalledWith('get_goal_v2', { id: 7 })
    expect(callTool).toHaveBeenCalledWith('heatmap_last_week')
  })
})
