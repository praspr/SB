import { useMemo } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'
import { AlertCircle, CalendarDays, CheckCircle2, Plus, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useJiraStatus, useTodayTasks, useTodayMeetings, useJiraTickets, useWebexStatus, useTasks } from '@/lib/queries'
import { webexAttentionFiltered } from '@/lib/triage'
import { ledgerProjects, ledgerSearch } from '@/lib/ledger'
import { listGoalsV2 } from '@/lib/goals'
import { useUiStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import { statusCategory } from '@/lib/jira-utils'
import { StatTile } from '@/components/ui/stat-tile'
import { Button } from '@/components/ui/button'
import { TaskList } from '@/components/tasks/TaskList'
import { TodoStats } from '@/components/tasks/TodoStats'
import { MeetingList } from '@/components/meetings/MeetingList'
import { DashboardInsights } from '@/components/landing/DashboardInsights'
import { HealthStrip } from '@/components/landing/HealthStrip'
import { ChatPanel } from '@/components/landing/ChatPanel'

export function LandingPage() {
  const setSettingsOpen = useUiStore((s) => s.setSettingsOpen)
  const setSettingsTab = useUiStore((s) => s.setSettingsTab)
  const openAddTodo = useUiStore((s) => s.openAddTodo)
  const { data: tasks, isLoading: tasksLoading } = useTodayTasks()
  const { data: allTasks } = useTasks()
  const { data: meetings, isLoading: meetingsLoading } = useTodayMeetings()
  const today = useMemo(() => {
    const now = new Date()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    return `${now.getFullYear()}-${month}-${day}`
  }, [])
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
  const jirasPending = (tickets.data ?? []).filter((ticket) => {
    const category = statusCategory(ticket.status)
    return category === 'open' || category === 'active'
  }).length
  const blockedCount = (tickets.data ?? []).filter((ticket) => ticket.status === 'Blocked').length
  const attentionCount = (attention.data?.length ?? 0) + blockedCount
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
      <HealthStrip jirasPending={jirasPending} />

      <section className="space-y-5 border-b border-border-subtle pb-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h1 className="text-24 font-semibold tracking-tight text-text-primary">Your day at a glance</h1>
          <Link to="/reports?template=daily" className="text-13 text-text-secondary hover:text-text-primary">
            View today&apos;s brief →
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <StatTile label="priorities today" value={tasks?.length ?? 0} icon={<CheckCircle2 size={14} />} tone="accent" />
          <StatTile label="meetings" value={meetings?.length ?? 0} icon={<CalendarDays size={14} />} tone="info" />
          <StatTile
            label="need attention"
            value={attentionCount}
            icon={<AlertCircle size={14} />}
            tone={attentionCount > 0 ? 'warning' : 'default'}
          />
        </div>
      </section>

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
                      <span
                        className={cn(
                          'flex h-4 w-4 shrink-0 items-center justify-center rounded-full border',
                          item.done
                            ? 'border-success-solid bg-success-solid/20 text-success-fg'
                            : 'border-border-strong text-transparent',
                        )}
                      >
                        <CheckCircle2 size={11} strokeWidth={3} />
                      </span>
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
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-accent-300" />
              <h2 className="text-16 font-semibold text-text-primary">Today&apos;s priorities</h2>
            </div>
            <div className="flex items-center gap-2">
              <Link to="/todos" className="text-12 text-text-secondary hover:text-text-primary">View all</Link>
              <Button variant="primary" onClick={() => openAddTodo()} className="px-2.5 py-1.5 text-12">
                <Plus size={14} />
                New todo
              </Button>
            </div>
          </div>
          <TodoStats tasks={allTasks ?? []} today={today} />
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

      <DashboardInsights tasks={tasks} tickets={tickets.data} />

      <details className="group rounded-xl border border-border-subtle bg-surface-1 shadow-card">
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
