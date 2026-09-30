import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useMeetings } from '@/lib/queries'
import { MeetingCard } from '@/components/meetings/MeetingCard'
import { PreMeetingCard } from '@/components/meetings/PreMeetingCard'
import { EmptyState } from '@/components/shared/EmptyState'
import { SkeletonRow } from '@/components/shared/SkeletonRow'
import { formatDateLabel } from '@/lib/utils'
import { proposeMeetingNotes, preMeetingContext } from '@/lib/triage'
import { Calendar } from 'lucide-react'

function isPastRecent(iso: string): boolean {
  const now = Date.now()
  const end = new Date(iso).getTime()
  return end < now && end > now - 24 * 60 * 60 * 1000
}

function nextMeetingWithinFifteen(meetings: ReturnType<typeof useMeetings>['data']) {
  if (!meetings) return null
  const now = Date.now()
  return meetings
    .filter((meeting) => {
      const start = new Date(meeting.start).getTime()
      return start > now && start - now <= 15 * 60 * 1000
    })
    .sort((a, b) => a.start.localeCompare(b.start))[0] ?? null
}

export function MeetingsPage() {
  const { data: meetings, isLoading, isError, error } = useMeetings()
  const [toast, setToast] = useState<string>()
  const nextMeeting = nextMeetingWithinFifteen(meetings)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (!nextMeeting || typeof window === 'undefined') return
    const key = `sb-premeet-dismissed-${nextMeeting.id}`
    const raw = window.localStorage.getItem(key)
    if (!raw) {
      setDismissed(false)
      return
    }
    setDismissed(Number(raw) > Date.now())
  }, [nextMeeting?.id])

  const preMeeting = useQuery({
    queryKey: ['triage', 'pre-meeting', nextMeeting?.id],
    queryFn: () => preMeetingContext(nextMeeting!.id),
    enabled: Boolean(nextMeeting && !dismissed),
    staleTime: 30_000,
  })

  const propose = useMutation({
    mutationFn: (meetingId: string) => proposeMeetingNotes(meetingId),
    onSuccess: (result) => {
      setToast(`${result.draft_count} proposals queued in /proposals`)
      setTimeout(() => setToast(undefined), 3000)
    },
  })

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
      {toast ? <div className="rounded-md border border-success/40 bg-success/10 p-3 text-13 text-success">{toast}</div> : null}
      {nextMeeting && !dismissed && preMeeting.data ? (
        <PreMeetingCard
          context={preMeeting.data}
          onDismiss={() => {
            if (typeof window !== 'undefined') {
              window.localStorage.setItem(`sb-premeet-dismissed-${nextMeeting.id}`, String(Date.now() + 30 * 60 * 1000))
            }
            setDismissed(true)
          }}
        />
      ) : null}

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
              <MeetingCard
                key={m.id}
                meeting={m}
              >
                {isPastRecent(m.end) ? (
                  <button
                    type="button"
                    onClick={() => propose.mutate(m.id)}
                    className="rounded-md border border-border-subtle px-2.5 py-1 text-12 text-text-secondary transition-colors duration-fast ease-out hover:border-border-strong hover:text-text-primary"
                  >
                    Propose notes
                  </button>
                ) : null}
              </MeetingCard>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
