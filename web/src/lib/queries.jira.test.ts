import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({
  callTool: vi.fn(),
}))

describe('jira queries', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('lists and filters tickets through list_jira_tickets', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([
      { key: 'CXP-1', title: 'Alpha', status: 'Open', priority: 'High', project: 'CXP' },
    ])
    const { listJiraTickets } = await import('./queries')
    const tickets = await listJiraTickets({
      status: 'Open',
      priority: 'High',
      project: 'CXP',
      q: 'alpha',
    })
    expect(callTool).toHaveBeenCalledWith('list_jira_tickets', {
      status: 'Open',
      priority: 'High',
      project: 'CXP',
      q: 'alpha',
    })
    expect(tickets[0].key).toBe('CXP-1')
  })

  it('syncs by pulling through sync_jira', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({
      updated_count: 1,
      added_count: 0,
      unchanged_count: 2,
      errors: [],
      duration_ms: 10,
      history_row_appended: true,
    })
    const { syncJira } = await import('./queries')
    const result = await syncJira()
    expect(callTool).toHaveBeenCalledWith('sync_jira')
    expect(result.updated_count).toBe(1)
  })

  it('surfaces a jira_status error', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockRejectedValue(new Error('MCP tool jira_status failed'))
    const { fetchJiraStatus } = await import('./queries')
    await expect(fetchJiraStatus()).rejects.toThrow(/jira_status/)
  })
})
