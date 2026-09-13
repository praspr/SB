import type { Meeting } from '@/lib/mock-data'
import { MeetingCard } from './MeetingCard'
import { EmptyState } from '@/components/shared/EmptyState'
import { SkeletonRow } from '@/components/shared/SkeletonRow'
import { Calendar } from 'lucide-react'

export function MeetingList({
  meetings,
  isLoading,
  emptyBody = 'No meetings scheduled.',
}: {
  meetings: Meeting[] | undefined
  isLoading?: boolean
  emptyBody?: string
}) {
  if (isLoading) return <SkeletonRow lines={4} />
  if (!meetings || meetings.length === 0) {
    return <EmptyState title="Nothing on the calendar" body={emptyBody} icon={<Calendar size={18} />} />
  }
  return (
    <div className="space-y-3">
      {meetings.map((m) => (
        <MeetingCard key={m.id} meeting={m} />
      ))}
    </div>
  )
}
