import { useMemo } from 'react'
import { useMeetings } from '@/lib/queries'
import { MeetingCard } from '@/components/meetings/MeetingCard'
import { EmptyState } from '@/components/shared/EmptyState'
import { SkeletonRow } from '@/components/shared/SkeletonRow'
import { formatDateLabel } from '@/lib/utils'
import { Calendar } from 'lucide-react'

export function MeetingsPage() {
  const { data: meetings, isLoading, isError, error } = useMeetings()

  const grouped = useMemo(() => {
    if (!meetings) return []
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const end = new Date(start)
    end.setDate(end.getDate() + 7)

    const inRange = meetings
      .filter((m) => {
        const d = new Date(m.start)
        return d >= start && d < end
      })
      .sort((a, b) => a.start.localeCompare(b.start))

    const groups = new Map<string, typeof inRange>()
    for (const m of inRange) {
      const key = new Date(m.start).toISOString().slice(0, 10)
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key)!.push(m)
    }
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b))
  }, [meetings])

  if (isLoading) return <SkeletonRow lines={5} />

  if (isError) {
    return (
      <EmptyState
        title="Meetings are unavailable"
        body={(error as Error)?.message ?? 'Sign in to Webex and sync, or check that sb is running.'}
        icon={<Calendar size={18} />}
      />
    )
  }

  if (grouped.length === 0) {
    return (
      <EmptyState
        title="No upcoming meetings"
        body="Nothing scheduled in the next 7 days."
        icon={<Calendar size={18} />}
      />
    )
  }

  return (
    <div className="space-y-6">
      {grouped.map(([dateKey, dayMeetings]) => (
        <section key={dateKey}>
          <div className="mb-3 flex items-center gap-2">
            <h2 className="text-16 font-semibold text-text-primary">{formatDateLabel(dateKey)}</h2>
            <span className="rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 tabular text-text-muted">
              {dayMeetings.length}
            </span>
          </div>
          <div className="space-y-3">
            {dayMeetings.map((m) => (
              <MeetingCard key={m.id} meeting={m} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
