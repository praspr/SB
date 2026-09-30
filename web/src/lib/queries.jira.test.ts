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

  it('hides closed tickets unless a status is requested', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([])
    const { listJiraTickets } = await import('./queries')
    await listJiraTickets({ status: 'active', projects: ['FSRE'], limit: 500 })
    expect(callTool).toHaveBeenCalledWith('list_jira_tickets', {
      hide_closed: true,
      projects: ['FSRE'],
      limit: 500,
    })
    await listJiraTickets({ status: 'Closed' })
    expect(callTool).toHaveBeenCalledWith('list_jira_tickets', { status: 'Closed' })
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

  it('tracks an issue through track_jira', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ key: 'CXP-77', tracked: true, errors: [] })
    const { trackJira } = await import('./queries')
    const result = await trackJira('https://cisco-cxe.atlassian.net/browse/CXP-77')
    expect(callTool).toHaveBeenCalledWith('track_jira', {
      issue: 'https://cisco-cxe.atlassian.net/browse/CXP-77',
    })
    expect(result.tracked).toBe(true)
  })

  it('untracks without deleting the local mirror', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ key: 'CXP-77', tracked: false, errors: [] })
    const { untrackJira } = await import('./queries')
    const result = await untrackJira('CXP-77')
    expect(callTool).toHaveBeenCalledWith('untrack_jira', { key: 'CXP-77' })
    expect(result.tracked).toBe(false)
  })

  it('surfaces a jira_status error', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockRejectedValue(new Error('MCP tool jira_status failed'))
    const { fetchJiraStatus } = await import('./queries')
    await expect(fetchJiraStatus()).rejects.toThrow(/jira_status/)
  })
})
