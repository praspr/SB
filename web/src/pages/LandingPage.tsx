import { CheckCircle2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useTodayTasks, useTodayMeetings, useTasks, useJiraTickets, useWebexAttention } from '@/lib/queries'
import { ledgerSearch } from '@/lib/ledger'
import { TaskList } from '@/components/tasks/TaskList'
import { MeetingList } from '@/components/meetings/MeetingList'
import { MorningBrief } from '@/components/landing/MorningBrief'
import { UsageStats } from '@/components/landing/UsageStats'
import { DashboardInsights } from '@/components/landing/DashboardInsights'
import { ChatPanel } from '@/components/landing/ChatPanel'
import { searchSignals } from '@/lib/signals'

export function LandingPage() {
  const { data: tasks, isLoading: tasksLoading } = useTodayTasks()
  const { data: meetings, isLoading: meetingsLoading } = useTodayMeetings()
  const attention = useWebexAttention()
  const allTasks = useTasks()
  const tickets = useJiraTickets()
  const signals = useQuery({
    queryKey: ['signals', 'dashboard'],
    queryFn: () => searchSignals(),
    staleTime: 30_000,
  })
  const ledgerDeltas = useQuery({
    queryKey: ['landing', 'ledger-deltas'],
    queryFn: () => ledgerSearch({ since: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), limit: 200 }),
    staleTime: 30_000,
  })

  return (
    <div className="space-y-6">
      <MorningBrief />

      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Ledger deltas overnight</div>
            <div className="mt-1 text-16 font-semibold text-text-primary">{ledgerDeltas.data?.length ?? 0} new ledger rows in the last 24 hours</div>
          </div>
          <Link to="/ledger?since=24h" className="rounded-lg border border-border-subtle bg-black/20 px-3 py-2 text-13 text-text-secondary transition hover:border-border-strong hover:text-text-primary">
            Open ledger
          </Link>
        </div>
      </section>

      <div>
        <h2 className="mb-2 text-xs uppercase tracking-wide text-neutral-500">Usage</h2>
        <UsageStats />
      </div>

      <DashboardInsights tasks={allTasks.data} tickets={tickets.data} signals={signals.data} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="grid content-start gap-6 2xl:grid-cols-2">
          <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Must-do</div>
                <h2 className="mt-1 text-16 font-semibold text-text-primary">Today's todos</h2>
              </div>
              <span className="flex items-center gap-1.5 rounded-full border border-border-subtle bg-black/20 px-2.5 py-1 text-12 text-text-secondary">
                <CheckCircle2 size={12} />
                {tasks?.length ?? 0}
              </span>
            </div>
            <div className="mt-4">
              <TaskList
                tasks={tasks}
                isLoading={tasksLoading}
                emptyTitle="You're all caught up"
                emptyBody="No must-do tasks for today. Add one to get started."
              />
            </div>
          </section>

          <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Calendar</div>
                <h2 className="mt-1 text-16 font-semibold text-text-primary">Meetings today</h2>
              </div>
              <span className="rounded-full border border-border-subtle bg-black/20 px-2.5 py-1 text-12 tabular text-text-secondary">
                {meetings?.length ?? 0}
              </span>
            </div>
            <div className="mt-4">
              <MeetingList meetings={meetings} isLoading={meetingsLoading} emptyBody="Nothing on today's calendar." />
              {attention.data && attention.data.length > 0 ? (
                <Link to="/webex" className="mt-3 inline-block text-13 text-text-secondary underline">
                  {attention.data.length} Webex messages need attention
                </Link>
              ) : null}
            </div>
          </section>
        </div>

        <ChatPanel />
      </div>
    </div>
  )
}
