import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({
  callTool: vi.fn(),
}))

describe('ledger wrappers', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('calls ledger_search with filters', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([])
    const { ledgerSearch } = await import('./ledger')
    await ledgerSearch({ q: 'reports', project: 'sb', limit: 8 })
    expect(callTool).toHaveBeenCalledWith('ledger_search', { q: 'reports', project: 'sb', limit: 8 })
  })

  it('calls ledger_register_project with upsert fields', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ project: 'sb', root_path: '/tmp/sb', changelog_path: '/tmp/sb/CHANGELOG.md', sync_mode: 'dual' })
    const { ledgerRegisterProject } = await import('./ledger')
    await ledgerRegisterProject({ project: 'sb', root_path: '/tmp/sb', sync_mode: 'dual' })
    expect(callTool).toHaveBeenCalledWith('ledger_register_project', {
      project: 'sb',
      root_path: '/tmp/sb',
      sync_mode: 'dual',
    })
  })
})
