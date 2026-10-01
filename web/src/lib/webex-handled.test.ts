import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({ callTool: vi.fn() }))

describe('webex handled client', () => {
  beforeEach(() => vi.resetModules())

  it('calls mark handled and unhandled tools', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ ok: true, message_id: 'msg-1', action: 'completed' })
    const api = await import('./webex-handled')

    await api.markHandled('msg-1', 'ignored')
    await api.markUnhandled('msg-1')

    expect(callTool).toHaveBeenCalledWith('webex_mark_handled', { message_id: 'msg-1', action: 'ignored' })
    expect(callTool).toHaveBeenCalledWith('webex_mark_unhandled', { message_id: 'msg-1' })
  })
})
