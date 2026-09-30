import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowRight, FileText, Sunrise } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { ledgerOpenThreads, ledgerSearch, type LedgerEntry } from '@/lib/ledger'
import { reportDaily } from '@/lib/reports'
import { fetchTasks, listMeetings } from '@/lib/queries'
import type { Meeting, Task } from '@/lib/mock-data'
import { formatTime } from '@/lib/utils'

const BRIEF_KEY_PREFIX = 'sb-brief-shown-'

function isTodayMeeting(meeting: Meeting): boolean {
  const start = new Date(meeting.start)
  const now = new Date()
  return start.getFullYear() === now.getFullYear()
    && start.getMonth() === now.getMonth()
    && start.getDate() === now.getDate()
}

type MorningBriefViewProps = {
  dateLabel: string
  open: boolean
  meetings: Meeting[]
  tasks: Task[]
  deltas: LedgerEntry[]
  threads: LedgerEntry[]
  loading?: boolean
  error?: string
  reportMarkdown?: string
  reportLoading?: boolean
  onDismiss: () => void
  onOpen: () => void
  onGenerateReport: () => void
}

export function MorningBriefView({
  dateLabel,
  open,
  meetings,
  tasks,
  deltas,
  threads,
  loading,
  error,
  reportMarkdown,
  reportLoading,
  onDismiss,
  onOpen,
  onGenerateReport,
}: MorningBriefViewProps) {
  if (!open) {
    return (
      <div className="flex justify-end">
        <Button variant="secondary" onClick={onOpen}>
          <Sunrise size={14} />
          Show today&apos;s brief
        </Button>
      </div>
    )
  }

  return (
    <>
      <section className="rounded-xl border border-border-strong bg-bg-panel/92 p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-12 uppercase tracking-[0.18em] text-text-muted">
              <Sunrise size={14} />
              Morning Brief
            </div>
            <h2 className="mt-2 text-20 font-semibold text-text-primary">Morning Brief · {dateLabel}</h2>
            <p className="mt-1 text-13 text-text-secondary">Start with meetings, priorities, overnight ledger movement, and unresolved threads.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={onGenerateReport} disabled={reportLoading}>
              <FileText size={14} />
              {reportLoading ? 'Generating report' : 'Generate daily report'}
            </Button>
            <Button variant="ghost" onClick={onDismiss}>Dismiss for today</Button>
          </div>
        </div>

        {error ? <div className="mt-4 rounded-md border border-danger/40 bg-danger/5 p-3 text-13 text-danger">{error}</div> : null}

        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          <section className="rounded-lg border border-border-subtle bg-black/20 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-14 font-semibold text-text-primary">Meetings today</h3>
              <Link to="/meetings" className="text-12 text-text-secondary underline">Open calendar</Link>
            </div>
            <div className="mt-3 text-13 text-text-secondary">{meetings.length} scheduled today.</div>
            <ul className="mt-3 space-y-2 text-13 text-text-secondary">
              {meetings.slice(0, 3).map((meeting) => (
                <li key={meeting.id} className="flex items-center justify-between gap-3 rounded-lg border border-border-subtle bg-bg-panel px-3 py-2">
                  <span className="truncate text-text-primary">{meeting.title}</span>
                  <span className="shrink-0 text-text-muted">{formatTime(meeting.start)}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border border-border-subtle bg-black/20 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-14 font-semibold text-text-primary">Top todos</h3>
              <Link to="/todos" className="text-12 text-text-secondary underline">Open todos</Link>
            </div>
            <ul className="mt-3 space-y-2 text-13 text-text-secondary">
              {tasks.slice(0, 3).map((task) => (
                <li key={task.id} className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-2">
                  <div className="text-text-primary">{task.title}</div>
                  <div className="mt-1 text-12 text-text-muted">priority {task.priority}</div>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border border-border-subtle bg-black/20 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-14 font-semibold text-text-primary">Overnight ledger deltas</h3>
              <Link to="/ledger?since=24h" className="inline-flex items-center gap-1 text-12 text-text-secondary underline">
                Open ledger
                <ArrowRight size={12} />
              </Link>
            </div>
            <div className="mt-3 text-13 text-text-secondary">{deltas.length} new entries in the last 24 hours.</div>
            <ul className="mt-3 space-y-2 text-13 text-text-secondary">
              {deltas.slice(0, 5).map((entry) => (
                <li key={entry.id} className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-2">
                  <div className="text-text-primary">{entry.summary}</div>
                  <div className="mt-1 text-12 text-text-muted">{entry.project} · {entry.action_verb}</div>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border border-border-subtle bg-black/20 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-14 font-semibold text-text-primary">Open threads</h3>
              <span className="text-12 text-text-muted">Top 5</span>
            </div>
            <ul className="mt-3 space-y-2 text-13 text-text-secondary">
              {threads.slice(0, 5).map((entry) => (
                <li key={entry.id} className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-2">
                  <div className="text-text-primary">{entry.summary}</div>
                  <div className="mt-1 text-12 text-text-muted">{entry.open_refs?.length ?? entry.refs.length} open refs</div>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {loading ? <div className="mt-4 text-12 text-text-muted">Refreshing the brief…</div> : null}
      </section>

      <Dialog open={Boolean(reportMarkdown || reportLoading)} onOpenChange={() => undefined}>
        <DialogContent className="max-w-2xl">
          <DialogTitle>Daily report</DialogTitle>
          <pre className="mt-4 max-h-[65vh] overflow-y-auto whitespace-pre-wrap rounded-lg border border-border-subtle bg-black/20 p-4 text-13 leading-6 text-text-secondary">
            {reportLoading ? 'Generating report…' : reportMarkdown}
          </pre>
        </DialogContent>
      </Dialog>
    </>
  )
}

export function MorningBrief() {
  const today = new Date().toISOString().slice(0, 10)
  const storageKey = `${BRIEF_KEY_PREFIX}${today}`
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const shown = window.localStorage.getItem(storageKey)
    setOpen(!shown)
  }, [storageKey])

  const meetings = useQuery({
    queryKey: ['brief', 'meetings', today],
    queryFn: async () => {
      const rows = await listMeetings()
      return rows.filter(isTodayMeeting)
    },
    staleTime: 30_000,
    enabled: open,
  })

  const todos = useQuery({
    queryKey: ['brief', 'todos'],
    queryFn: async () => {
      const rows = await fetchTasks()
      return rows.filter((task) => !task.is_completed).sort((a, b) => a.priority - b.priority)
    },
    staleTime: 30_000,
    enabled: open,
  })

  const deltas = useQuery({
    queryKey: ['brief', 'ledger-deltas'],
    queryFn: () => ledgerSearch({ since: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), limit: 50 }),
    staleTime: 30_000,
    enabled: open,
  })

  const threads = useQuery({
    queryKey: ['brief', 'threads'],
    queryFn: () => ledgerOpenThreads(),
    staleTime: 30_000,
    enabled: open,
  })

  const dailyReport = useMutation({ mutationFn: () => reportDaily(today) })

  const error = meetings.error || todos.error || deltas.error || threads.error
  const dateLabel = useMemo(() => new Date(today).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }), [today])

  function dismiss() {
    if (typeof window !== 'undefined') window.localStorage.setItem(storageKey, '1')
    setOpen(false)
  }

  return (
    <MorningBriefView
      dateLabel={dateLabel}
      open={open}
      meetings={meetings.data ?? []}
      tasks={todos.data ?? []}
      deltas={deltas.data ?? []}
      threads={threads.data ?? []}
      loading={meetings.isLoading || todos.isLoading || deltas.isLoading || threads.isLoading}
      error={error instanceof Error ? error.message : undefined}
      reportMarkdown={dailyReport.data?.markdown}
      reportLoading={dailyReport.isPending}
      onDismiss={dismiss}
      onOpen={() => setOpen(true)}
      onGenerateReport={() => dailyReport.mutate()}
    />
  )
}
