import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({
  callTool: vi.fn(),
}))

describe('report wrappers', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('calls report_daily with date and project', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ markdown: '# Daily', citations: [] })
    const { reportDaily } = await import('./reports')
    await reportDaily('2026-09-30', 'sb')
    expect(callTool).toHaveBeenCalledWith('report_daily', { date: '2026-09-30', project: 'sb' })
  })

  it('calls report_query with freeform filters', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ markdown: '# Query', citations: [1] })
    const { reportQuery } = await import('./reports')
    await reportQuery({ q: 'ledger', since: '2026-09-01T00:00:00Z', until: '2026-10-01T00:00:00Z' })
    expect(callTool).toHaveBeenCalledWith('report_query', {
      q: 'ledger',
      since: '2026-09-01T00:00:00Z',
      until: '2026-10-01T00:00:00Z',
    })
  })

  it('calls report_perf_checkin with shape and voice', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ markdown: '# Perf check-in', citations: [] })
    const { reportPerfCheckin } = await import('./reports')
    await reportPerfCheckin({ shape: 'one-improvement', voice: 'third-person' })
    expect(callTool).toHaveBeenCalledWith('report_perf_checkin', {
      shape: 'one-improvement',
      voice: 'third-person',
    })
  })

  it('calls report_perf_checkin with no args by default', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ markdown: '# Perf check-in', citations: [] })
    const { reportPerfCheckin } = await import('./reports')
    await reportPerfCheckin()
    expect(callTool).toHaveBeenCalledWith('report_perf_checkin', {})
  })
})
