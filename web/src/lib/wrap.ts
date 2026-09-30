import { callTool } from './mcp'

export type WrapResult = {
  date: string
  wrap_md: string
  dry_run: boolean
  persisted: boolean
  proposals: Proposal[]
}

export type Proposal = {
  id: number
  type: string
  title: string
  status: string
  payload: string
  target_path?: string | null
}

export function wrapDay(): Promise<WrapResult> {
  return callTool<WrapResult>('wrap_day', { dry_run: false })
}

export function listProposals(): Promise<Proposal[]> {
  return callTool<Proposal[]>('list_proposals', { status: 'pending' })
}

export function approveProposal(proposalId: number): Promise<Proposal> {
  return callTool<Proposal>('approve_proposal', { proposal_id: proposalId })
}

export function rejectProposal(proposalId: number): Promise<Proposal> {
  return callTool<Proposal>('reject_proposal', { proposal_id: proposalId })
}
