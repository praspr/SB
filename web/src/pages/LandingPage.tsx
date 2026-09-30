import { useQuery } from '@tanstack/react-query'
import { AlertCircle, ArrowRight, CalendarDays, CheckCircle2, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTodayTasks, useTodayMeetings, useJiraTickets } from '@/lib/queries'
import { webexAttentionFiltered } from '@/lib/triage'
import { TaskList } from '@/components/tasks/TaskList'
import { MeetingList } from '@/components/meetings/MeetingList'
import { ChatPanel } from '@/components/landing/ChatPanel'

export function LandingPage() {
  const { data: tasks, isLoading: tasksLoading } = useTodayTasks()
  const { data: meetings, isLoading: meetingsLoading } = useTodayMeetings()
  const attention = useQuery({
    queryKey: ['triage', 'attention'],
    queryFn: () => webexAttentionFiltered(30),
    staleTime: 30_000,
  })
  const tickets = useJiraTickets()
  const blockedTickets = (tickets.data ?? []).filter((ticket) => ticket.status === 'Blocked')
  const attentionCount = (attention.data?.length ?? 0) + blockedTickets.length

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <h1 className="text-24 font-semibold tracking-tight text-text-primary">Your day at a glance</h1>
          <p className="mt-1 text-13 text-text-secondary">
            {tasks?.length ?? 0} priorities · {meetings?.length ?? 0} meetings · {attentionCount} need attention
          </p>
        </div>
        <Link to="/todos" className="inline-flex items-center gap-1.5 text-13 font-medium text-text-secondary hover:text-text-primary">
          Plan your day
          <ArrowRight size={14} />
        </Link>
      </section>

      <section className="rounded-xl border border-warning/25 bg-warning/5 px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-warning/10 text-warning">
            <AlertCircle size={16} />
          </span>
          <div>
            <h2 className="text-14 font-semibold text-text-primary">Needs attention</h2>
            <p className="mt-0.5 text-12 text-text-secondary">
              {attentionCount === 0
                ? 'Nothing urgent is waiting for you.'
                : `${attention.data?.length ?? 0} Webex messages and ${blockedTickets.length} blocked JIRAs.`}
            </p>
          </div>
          {attentionCount > 0 ? (
            <Link to="/attention" className="ml-auto inline-flex items-center gap-1 text-12 font-medium text-text-secondary hover:text-text-primary">
              Review
              <ArrowRight size={13} />
            </Link>
          ) : null}
        </div>
      </section>

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-accent-300" />
              <h2 className="text-16 font-semibold text-text-primary">Today&apos;s priorities</h2>
            </div>
            <Link to="/todos" className="text-12 text-text-secondary hover:text-text-primary">View all</Link>
          </div>
          <TaskList
            tasks={tasks?.slice(0, 3)}
            isLoading={tasksLoading}
            emptyTitle="No priorities for today"
            emptyBody="Add a todo when something needs your attention."
          />
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CalendarDays size={16} className="text-accent-300" />
              <h2 className="text-16 font-semibold text-text-primary">Upcoming meetings</h2>
            </div>
            <Link to="/meetings" className="text-12 text-text-secondary hover:text-text-primary">Open calendar</Link>
          </div>
          <MeetingList meetings={meetings?.slice(0, 3)} isLoading={meetingsLoading} emptyBody="Nothing else on today's calendar." />
        </section>
      </div>

      <details className="group rounded-xl border border-border-subtle bg-bg-panel/60">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-14 font-medium text-text-secondary hover:text-text-primary">
          <Sparkles size={15} className="text-accent-300" />
          Ask your second brain
          <span className="ml-auto text-12 text-text-muted group-open:hidden">Open</span>
        </summary>
        <div className="border-t border-border-subtle p-3">
          <ChatPanel />
        </div>
      </details>
    </div>
  )
}
