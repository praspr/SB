import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({ callTool: vi.fn() }))

describe('url hints client', () => {
  beforeEach(() => vi.resetModules())

  it('calls parse_url_hint', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ kind: 'jira', extracted: { key: 'CXP-1' }, suggested_action: 'track_jira' })
    const api = await import('./url-hints')
    await api.parseUrlHint('https://example.com/browse/CXP-1')
    expect(callTool).toHaveBeenCalledWith('parse_url_hint', { url: 'https://example.com/browse/CXP-1' })
  })
})
