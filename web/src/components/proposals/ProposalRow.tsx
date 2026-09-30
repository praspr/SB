import { Check, X } from 'lucide-react'
import type { Proposal } from '@/lib/proposals'
import { Button } from '@/components/ui/button'

export function ProposalRow({
  proposal,
  acting,
  onApprove,
  onReject,
}: {
  proposal: Proposal
  acting?: boolean
  onApprove: (proposal: Proposal) => void
  onReject: (proposal: Proposal) => void
}) {
  const approveDisabled = acting || proposal.type !== 'changelog'

  return (
    <div className="rounded-xl border border-border-subtle bg-bg-panel/92 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-12 text-text-muted">
            <span className="rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 uppercase tracking-[0.16em]">
              {proposal.type}
            </span>
            <span>{proposal.created_at ?? 'pending'}</span>
          </div>
          <h2 className="mt-2 text-14 font-semibold text-text-primary">{proposal.title}</h2>
          {proposal.payload ? <pre className="mt-3 whitespace-pre-wrap text-13 leading-6 text-text-secondary">{proposal.payload}</pre> : null}
          {proposal.type !== 'changelog' ? (
            <p className="mt-3 text-12 text-text-muted">This proposal type is read-only in the portal for now.</p>
          ) : null}
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="secondary" onClick={() => onApprove(proposal)} disabled={approveDisabled}>
            <Check size={14} />
            Accept
          </Button>
          <Button variant="ghost" onClick={() => onReject(proposal)} disabled={acting}>
            <X size={14} />
            Reject
          </Button>
        </div>
      </div>
    </div>
  )
}
