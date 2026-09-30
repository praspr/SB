import { callTool } from './mcp'

export type Proposal = {
  id: number
  type: string
  title: string
  status: string
  payload: string
  target_path?: string | null
  signal_refs?: Array<Record<string, unknown>>
  created_at?: string
  updated_at?: string | null
}

export function listProposals(status = 'pending'): Promise<Proposal[]> {
  return callTool<Proposal[]>('list_proposals', { status })
}

export function approveProposal(proposalId: number): Promise<Proposal> {
  return callTool<Proposal>('approve_proposal', { proposal_id: proposalId })
}

export function rejectProposal(proposalId: number): Promise<Proposal> {
  return callTool<Proposal>('reject_proposal', { proposal_id: proposalId })
}
