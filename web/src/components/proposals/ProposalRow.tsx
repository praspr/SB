import { Check, X } from 'lucide-react'
import type { Proposal } from '@/lib/proposals'
import { Button } from '@/components/ui/button'
import { useUiStore } from '@/lib/store'

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
  const openAddTodo = useUiStore((state) => state.openAddTodo)

  let todoPayload: { title?: string; priority?: number; meeting_id?: string } = {}
  if (proposal.type === 'todo') {
    try {
      todoPayload = JSON.parse(proposal.payload) as typeof todoPayload
    } catch {
      todoPayload = {}
    }
  }

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
          {proposal.type === 'todo' ? (
            <Button
              variant="secondary"
              onClick={() =>
                openAddTodo({
                  title: todoPayload.title || proposal.title.replace(/^Todo ·\s*/, ''),
                  description: `Meeting follow-up${todoPayload.meeting_id ? ` · ${todoPayload.meeting_id}` : ''}`,
                  priority:
                    todoPayload.priority && todoPayload.priority >= 1 && todoPayload.priority <= 4
                      ? (todoPayload.priority as 1 | 2 | 3 | 4)
                      : 2,
                  external_source: 'webex-meeting',
                  external_ref: `proposal:${proposal.id}`,
                })
              }
            >
              Create todo
            </Button>
          ) : null}
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
