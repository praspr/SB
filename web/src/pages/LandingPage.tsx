import { useQueries, useQuery } from '@tanstack/react-query'
import { AlertCircle, ArrowRight, CalendarDays, CheckCircle2, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useJiraStatus, useTodayTasks, useTodayMeetings, useJiraTickets, useWebexStatus } from '@/lib/queries'
import { webexAttentionFiltered } from '@/lib/triage'
import { ledgerProjects, ledgerSearch } from '@/lib/ledger'
import { listGoalsV2 } from '@/lib/goals'
import { useUiStore } from '@/lib/store'
import { TaskList } from '@/components/tasks/TaskList'
import { MeetingList } from '@/components/meetings/MeetingList'
import { ChatPanel } from '@/components/landing/ChatPanel'

export function LandingPage() {
  const setSettingsOpen = useUiStore((s) => s.setSettingsOpen)
  const setSettingsTab = useUiStore((s) => s.setSettingsTab)
  const { data: tasks, isLoading: tasksLoading } = useTodayTasks()
  const { data: meetings, isLoading: meetingsLoading } = useTodayMeetings()
  const attention = useQuery({
    queryKey: ['triage', 'attention'],
    queryFn: () => webexAttentionFiltered(30),
    staleTime: 30_000,
  })
  const tickets = useJiraTickets()
  const webexStatus = useWebexStatus()
  const jiraStatus = useJiraStatus()
  const [ledgerPreview, projects, goals] = useQueries({
    queries: [
      {
        queryKey: ['landing', 'ledger-preview'],
        queryFn: () => ledgerSearch({ limit: 1 }),
        staleTime: 30_000,
        retry: 1,
      },
      {
        queryKey: ['landing', 'projects'],
        queryFn: ledgerProjects,
        staleTime: 30_000,
        retry: 1,
      },
      {
        queryKey: ['landing', 'goals'],
        queryFn: () => listGoalsV2({ status: 'active' }),
        staleTime: 30_000,
        retry: 1,
      },
    ],
  })
  const blockedTickets = (tickets.data ?? []).filter((ticket) => ticket.status === 'Blocked')
  const attentionHighlights = [
    ...(attention.data ?? []).map((item) => ({
      id: item.id,
      sender: item.sender_name,
      preview: item.preview,
      kind: item.triage_kind === 'dm' ? 'DM' : item.triage_kind === 'mention' ? 'Mention' : 'Webex',
    })),
    ...blockedTickets.map((ticket) => ({
      id: ticket.key,
      sender: ticket.key,
      preview: ticket.title,
      kind: 'Blocked JIRA',
    })),
  ]
  const attentionCount = attentionHighlights.length
  const topAttention = attentionHighlights.slice(0, 2)
  const overflowAttention = attentionCount - topAttention.length
  const ledgerCount = ledgerPreview.data?.length ?? 0
  const isFirstRunEmpty = (tasks?.length ?? 0) + (tickets.data?.length ?? 0) + attentionCount + ledgerCount === 0
  const checklist: Array<
    | { label: string; done: boolean; href: string }
    | { label: string; done: boolean; action: () => void }
  > = [
    { label: 'Sign in to Webex', done: Boolean(webexStatus.data?.authenticated), href: '/webex/login' },
    { label: 'Add JIRA token', done: Boolean(jiraStatus.data?.atlassian_reachable), action: () => { setSettingsTab('connections'); setSettingsOpen(true) } },
    { label: 'Log first ledger', done: ledgerCount > 0, href: '/reports?template=daily' },
    { label: 'Enroll a project', done: (projects.data?.length ?? 0) > 0, action: () => { setSettingsTab('projects'); setSettingsOpen(true) } },
    { label: 'Set up a goal', done: (goals.data?.length ?? 0) > 0, href: '/goals?new' },
  ]
  const allChecklistDone = checklist.every((item) => item.done)

  return (
    <div className="space-y-6">
      {attentionCount > 0 ? (
        <section className="rounded-2xl border border-warning/25 bg-warning/5 px-5 py-4">
          <div className="flex flex-wrap items-start gap-4">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-warning/10 text-warning">
              <AlertCircle size={18} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-16 font-semibold text-text-primary">Attention is stacking up</h2>
                <span className="rounded-full border border-warning/30 bg-warning/10 px-2 py-0.5 text-12 tabular text-warning">
                  {attentionCount} waiting
                </span>
              </div>
              <div className="mt-3 space-y-2">
                {topAttention.map((item) => (
                  <div key={item.id} className="rounded-xl border border-warning/20 bg-black/20 px-3 py-2.5">
                    <div className="flex items-start gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="text-13 font-medium text-text-primary">{item.sender}</div>
                        <div className="mt-0.5 truncate text-12 text-text-secondary">{item.preview}</div>
                      </div>
                      <span className="shrink-0 rounded-full border border-border-subtle bg-bg-panel px-2 py-0.5 text-11 uppercase tracking-[0.18em] text-text-muted">
                        {item.kind}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              {overflowAttention > 0 ? (
                <div className="mt-3 text-12 text-text-secondary">+{overflowAttention} more waiting</div>
              ) : null}
            </div>
            <Link to="/attention" className="inline-flex items-center gap-1.5 text-13 font-medium text-text-secondary hover:text-text-primary">
              Open inbox
              <ArrowRight size={14} />
            </Link>
          </div>
        </section>
      ) : (
        <section className="flex flex-wrap items-end justify-between gap-4 border-b border-border-subtle pb-5">
          <div>
            <h1 className="text-24 font-semibold tracking-tight text-text-primary">Your day at a glance</h1>
            <p className="mt-1 text-13 text-text-secondary">
              {tasks?.length ?? 0} priorities · {meetings?.length ?? 0} meetings · {attentionCount} need attention
            </p>
          </div>
          <Link to="/reports?template=daily" className="text-13 text-text-secondary hover:text-text-primary">
            View today&apos;s brief →
          </Link>
        </section>
      )}

      {isFirstRunEmpty && !allChecklistDone ? (
        <section className="rounded-2xl border border-border-subtle bg-bg-panel/80 p-5">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-500/10 text-accent-300">
              <Sparkles size={18} />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-16 font-semibold text-text-primary">Get started</h2>
              <p className="mt-1 text-13 text-text-secondary">A few quick setup steps will turn this into a real working dashboard.</p>
              <div className="mt-4 space-y-2">
                {checklist.map((item) => (
                  <div key={item.label} className="flex items-center justify-between gap-3 rounded-xl border border-border-subtle bg-black/20 px-3 py-2.5">
                    <div className="flex items-center gap-2 text-13 text-text-primary">
                      <span className={item.done ? 'text-success' : 'text-text-muted'}>{item.done ? '[x]' : '[ ]'}</span>
                      <span>{item.label}</span>
                    </div>
                    {'href' in item ? (
                      <Link to={item.href} className="text-12 text-text-secondary hover:text-text-primary">
                        Open
                      </Link>
                    ) : (
                      <button type="button" onClick={item.action} className="text-12 text-text-secondary hover:text-text-primary">
                        Open
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-accent-300" />
              <h2 className="text-16 font-semibold text-text-primary">Today&apos;s priorities</h2>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/todos" className="text-12 text-text-secondary hover:text-text-primary">Plan your day</Link>
              <Link to="/todos" className="text-12 text-text-secondary hover:text-text-primary">View all</Link>
            </div>
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
