import type { JiraTicket } from '@/lib/mock-data'
import { JiraTicketRow } from './JiraTicketRow'
import { EmptyState } from '@/components/shared/EmptyState'
import { SkeletonRow } from '@/components/shared/SkeletonRow'

export function JiraTicketList({
  tickets,
  isLoading,
  emptyTitle = 'No tickets match',
  emptyBody = 'Try a different filter combination.',
}: {
  tickets: JiraTicket[] | undefined
  isLoading?: boolean
  emptyTitle?: string
  emptyBody?: string
}) {
  if (isLoading) return <SkeletonRow lines={5} />
  if (!tickets || tickets.length === 0) {
    return <EmptyState title={emptyTitle} body={emptyBody} />
  }

  return (
    <div className="space-y-2">
      {tickets.map((ticket) => (
        <JiraTicketRow key={ticket.key} ticket={ticket} />
      ))}
    </div>
  )
}
