import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  approveProposal,
  listProposals,
  rejectProposal,
  wrapDay,
  type Proposal,
  type WrapResult,
} from '@/lib/wrap'

export function WrapView({
  wrap,
  proposals,
  error,
  wrapping,
  onWrap,
  onApprove,
  onReject,
}: {
  wrap?: WrapResult | null
  proposals: Proposal[]
  error?: string
  wrapping: boolean
  onWrap: () => void
  onApprove: (id: number) => void
  onReject: (id: number) => void
}) {
  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Wrap</h1>
          <p className="mt-1 text-13 text-text-secondary">
            Evidence-backed day wrap and local CHANGELOG proposals.
          </p>
        </div>
        <button type="button" onClick={onWrap} className="rounded-lg border border-border-subtle px-3 py-1.5 text-13">
          {wrapping ? 'Wrapping' : 'Wrap day'}
        </button>
      </div>
      {error && <p className="text-13 text-danger">{error}</p>}
      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <h2 className="text-14 font-semibold text-text-primary">Wrap</h2>
        <pre className="mt-3 whitespace-pre-wrap text-13 text-text-secondary">
          {wrap?.wrap_md || 'No wrap yet.'}
        </pre>
      </section>
      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <h2 className="text-14 font-semibold text-text-primary">Proposals</h2>
        {proposals.length === 0 ? (
          <p className="mt-2 text-13 text-text-muted">No pending proposals.</p>
        ) : (
          <ul className="mt-3 space-y-3">
            {proposals.map((proposal) => (
              <li key={proposal.id} className="rounded-lg border border-border-subtle p-3">
                <p className="text-13 font-medium text-text-primary">{proposal.title}</p>
                <pre className="mt-2 whitespace-pre-wrap text-12 text-text-secondary">{proposal.payload}</pre>
                <div className="mt-2 flex gap-2">
                  <button type="button" onClick={() => onApprove(proposal.id)} className="text-13 text-text-primary">
                    Approve
                  </button>
                  <button type="button" onClick={() => onReject(proposal.id)} className="text-13 text-text-secondary">
                    Reject
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

export function WrapPage() {
  const client = useQueryClient()
  const proposals = useQuery({ queryKey: ['proposals'], queryFn: listProposals })
  const wrap = useMutation({
    mutationFn: () => wrapDay(),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['proposals'] })
    },
  })
  const decide = useMutation({
    mutationFn: (action: { id: number; approve: boolean }) =>
      action.approve ? approveProposal(action.id) : rejectProposal(action.id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['proposals'] })
    },
  })
  const failed = proposals.isError || wrap.isError || decide.isError
  return (
    <WrapView
      wrap={wrap.data}
      proposals={proposals.data ?? []}
      error={failed ? 'Could not load wrap.' : undefined}
      wrapping={wrap.isPending}
      onWrap={() => wrap.mutate()}
      onApprove={(id) => decide.mutate({ id, approve: true })}
      onReject={(id) => decide.mutate({ id, approve: false })}
    />
  )
}
