import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { ProposalRow } from '@/components/proposals/ProposalRow'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/button'
import { approveProposal, listProposals, rejectProposal, type Proposal } from '@/lib/proposals'

export function ProposalsView({
  proposals,
  loading,
  error,
  refreshing,
  actingId,
  onRefresh,
  onApprove,
  onReject,
}: {
  proposals: Proposal[]
  loading?: boolean
  error?: string
  refreshing?: boolean
  actingId?: number | null
  onRefresh: () => void
  onApprove: (proposal: Proposal) => void
  onReject: (proposal: Proposal) => void
}) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Proposals</h1>
          <p className="mt-1 text-13 text-text-secondary">Review pending LLM-drafted proposals before anything writes to disk.</p>
        </div>
        <Button variant="secondary" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : undefined} />
          Refresh
        </Button>
      </div>

      {error ? <div className="rounded-md border border-danger/40 bg-danger/5 p-3 text-13 text-danger">{error}</div> : null}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-xl border border-border-subtle bg-bg-panel" />
          ))}
        </div>
      ) : proposals.length === 0 ? (
        <EmptyState
          title="Nothing pending"
          body="LLM-drafted proposals will show up here."
        />
      ) : (
        <div className="space-y-3">
          {proposals.map((proposal) => (
            <ProposalRow
              key={proposal.id}
              proposal={proposal}
              acting={actingId === proposal.id}
              onApprove={onApprove}
              onReject={onReject}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function ProposalsPage() {
  const queryClient = useQueryClient()
  const proposals = useQuery({ queryKey: ['proposals', 'pending'], queryFn: () => listProposals('pending') })
  const decide = useMutation({
    mutationFn: async ({ proposal, approve }: { proposal: Proposal; approve: boolean }) => {
      // TODO: wire non-changelog proposal kinds once the backend approve path supports them.
      return approve ? approveProposal(proposal.id) : rejectProposal(proposal.id)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['proposals'] })
    },
  })

  return (
    <ProposalsView
      proposals={proposals.data ?? []}
      loading={proposals.isLoading}
      error={proposals.isError ? 'Could not load proposals.' : decide.isError ? 'Could not update that proposal.' : undefined}
      refreshing={proposals.isFetching}
      actingId={decide.variables?.proposal.id ?? null}
      onRefresh={() => {
        void proposals.refetch()
      }}
      onApprove={(proposal) => decide.mutate({ proposal, approve: true })}
      onReject={(proposal) => decide.mutate({ proposal, approve: false })}
    />
  )
}
