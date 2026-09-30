import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({ callTool: vi.fn() }))

describe('webex post client', () => {
  beforeEach(() => vi.resetModules())

  it('calls webex_post_message', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ posted: true })
    const api = await import('./webex-post')
    await api.webexPostMessage('space-1', 'hello', 'markdown')
    expect(callTool).toHaveBeenCalledWith('webex_post_message', {
      space_id: 'space-1',
      markdown: 'hello',
      message_type: 'markdown',
    })
  })
})
