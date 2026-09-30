import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({
  callTool: vi.fn(),
}))

describe('proposal wrappers', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('lists pending proposals by default', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([])
    const { listProposals } = await import('./proposals')
    await listProposals()
    expect(callTool).toHaveBeenCalledWith('list_proposals', { status: 'pending' })
  })

  it('approves and rejects by proposal id', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({ id: 7, status: 'executed' })
    const { approveProposal, rejectProposal } = await import('./proposals')
    await approveProposal(7)
    expect(callTool).toHaveBeenCalledWith('approve_proposal', { proposal_id: 7 })
    await rejectProposal(8)
    expect(callTool).toHaveBeenCalledWith('reject_proposal', { proposal_id: 8 })
  })
})
