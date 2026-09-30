import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({ callTool: vi.fn() }))

describe('bulk jira client', () => {
  beforeEach(() => vi.resetModules())

  it('calls bulk import tool', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ imported: 0, skipped: 0, ticket_keys: [] })
    const api = await import('./bulk-jira')
    await api.bulkImportJiraToTodos({ statuses: ['Open'], dry_run: true })
    expect(callTool).toHaveBeenCalledWith('bulk_import_jira_to_todos', { statuses: ['Open'], dry_run: true })
  })
})
