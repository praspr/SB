import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({ callTool: vi.fn() }))

describe('webex mute client', () => {
  beforeEach(() => vi.resetModules())

  it('calls mute and list tools', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([])
    const api = await import('./webex-mute')
    await api.muteSpace('space-1')
    await api.unmuteSpace('space-1')
    await api.listMutedSpaces()
    expect(callTool).toHaveBeenCalledWith('mute_space', { space_id: 'space-1' })
    expect(callTool).toHaveBeenCalledWith('unmute_space', { space_id: 'space-1' })
    expect(callTool).toHaveBeenCalledWith('list_muted_spaces')
  })
})
