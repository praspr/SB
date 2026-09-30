import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({
  callTool: vi.fn(),
}))

vi.mock('./ledger', async () => {
  const actual = await vi.importActual<typeof import('./ledger')>('./ledger')
  return {
    ...actual,
    ledgerLog: vi.fn(),
  }
})

describe('triage client', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('calls the triage MCP tools', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([])
    const api = await import('./triage')
    await api.webexAttentionRanked(12)
    await api.preMeetingContext('meet-1')
    await api.proposeMeetingNotes('meet-1')
    expect(callTool).toHaveBeenCalledWith('webex_attention_ranked', { limit: 12 })
    expect(callTool).toHaveBeenCalledWith('pre_meeting_context', { meeting_id: 'meet-1' })
    expect(callTool).toHaveBeenCalledWith('propose_meeting_notes', { meeting_id: 'meet-1' })
  })

  it('wraps ritual tools into report-friendly markdown', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool)
      .mockResolvedValueOnce({ date: '2026-09-30', plan_md: '# Plan' })
      .mockResolvedValueOnce({ date: '2026-09-30', wrap_md: '# Wrap' })
      .mockResolvedValueOnce({ date: '2026-09-30', bullets: ['Did the thing'] })
    const api = await import('./triage')
    await expect(api.reportToday()).resolves.toEqual({ markdown: '# Plan', citations: [], date: '2026-09-30' })
    await expect(api.reportWrap()).resolves.toEqual({ markdown: '# Wrap', citations: [], date: '2026-09-30' })
    await expect(api.reportStandup()).resolves.toEqual({ markdown: '- Did the thing', citations: [], date: '2026-09-30' })
  })
})
