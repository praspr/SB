import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CalendarClock, CheckCircle2, Circle, Search } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { bulkImportJiraToTodos } from '@/lib/bulk-jira'
import { fetchRichTasks } from '@/lib/todos-rich'
import { listGoalsV2 } from '@/lib/goals'
import { listJiraTickets } from '@/lib/queries'
import { TaskList } from '@/components/tasks/TaskList'
import { QuickAddInput, type QuickAddInputHandle } from '@/components/tasks/QuickAddInput'
import type { Priority } from '@/lib/mock-data'
import { cn } from '@/lib/utils'
import { useUiStore } from '@/lib/store'
import { useToast } from '@/lib/useToast'
import {
  organizeTodos,
  summarizeTodos,
  type TodoSort,
  type TodoStatusFilter,
} from '@/lib/todo-groups'

export function TodosPage() {
  const client = useQueryClient()
  const { data: tasks, isLoading } = useQuery({ queryKey: ['tasks', 'rich'], queryFn: fetchRichTasks })
  const goals = useQuery({ queryKey: ['goals-v2', 'todos'], queryFn: async () => listGoalsV2(), staleTime: 30_000 })
  const jiraTickets = useQuery({ queryKey: ['jira', 'tickets', 'todos-import-count'], queryFn: () => listJiraTickets({ limit: 200 }), staleTime: 30_000 })
  const [searchParams] = useSearchParams()
  const requestedStatus = searchParams.get('status')
  const initialStatus: TodoStatusFilter =
    requestedStatus === 'all' || requestedStatus === 'completed' ? requestedStatus : 'open'
  const [status, setStatus] = useState<TodoStatusFilter>(initialStatus)
  const [priority, setPriority] = useState<Priority | 'all'>('all')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<TodoSort>('priority')
  const [importOpen, setImportOpen] = useState(false)
  const [importStatuses, setImportStatuses] = useState<string[]>(['Open', 'In Progress'])
  const [importPriority, setImportPriority] = useState<'all' | 'Highest' | 'High' | 'Medium' | 'Low' | 'Lowest'>('all')
  const [dryRun, setDryRun] = useState(true)
  const quickAddRef = useRef<QuickAddInputHandle>(null)
  const focusQuickAddSignal = useUiStore((s) => s.focusQuickAddSignal)
  const showToast = useToast((s) => s.show)
  const importJira = useMutation({
    mutationFn: () => bulkImportJiraToTodos({ statuses: importStatuses, dry_run: dryRun }),
    onSuccess: (result) => {
      showToast({ kind: 'success', message: `${result.imported} imported, ${result.skipped} skipped` })
      setImportOpen(false)
      void client.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  useEffect(() => {
    if (focusQuickAddSignal > 0) {
      quickAddRef.current?.focus()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusQuickAddSignal])

  const today = useMemo(() => {
    const now = new Date()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    return `${now.getFullYear()}-${month}-${day}`
  }, [])
  const summary = useMemo(() => summarizeTodos(tasks ?? [], today), [tasks, today])
  const groups = useMemo(
    () => organizeTodos(tasks ?? [], { status, priority, query, sort, today }),
    [priority, query, sort, status, tasks, today],
  )
  const visibleCount = groups.reduce((count, group) => count + group.tasks.length, 0)

  const goalTitles = useMemo(() => Object.fromEntries((goals.data ?? []).map((goal) => [goal.id, goal.title])), [goals.data])
  const jiraPreview = useMemo(() => {
    const rows = jiraTickets.data ?? []
    return rows.filter((ticket) => importStatuses.length === 0 || importStatuses.includes(ticket.status))
      .filter((ticket) => importPriority === 'all' || ticket.priority === importPriority)
  }, [importPriority, importStatuses, jiraTickets.data])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-[280px] flex-1">
          <QuickAddInput ref={quickAddRef} />
        </div>
        <Button variant="secondary" onClick={() => setImportOpen(true)}>
          Create todos from JIRA{jiraTickets.data ? ` (${jiraTickets.data.length})` : ''}
        </Button>
      </div>

      <div className="grid grid-cols-2 overflow-hidden rounded-xl border border-border-subtle bg-bg-panel/60 sm:grid-cols-4">
        {[
          { label: 'Overdue', value: summary.overdue, icon: AlertTriangle, tone: 'text-danger' },
          { label: 'Due today', value: summary.today, icon: CalendarClock, tone: 'text-warning' },
          { label: 'Open', value: summary.open, icon: Circle, tone: 'text-accent-300' },
          { label: 'Completed', value: summary.completed, icon: CheckCircle2, tone: 'text-success' },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-3 border-b border-border-subtle px-4 py-3 last:border-0 sm:border-b-0 sm:border-r">
            <item.icon size={15} className={item.tone} />
            <div>
              <div className="text-18 font-semibold tabular text-text-primary">{item.value}</div>
              <div className="text-11 uppercase tracking-[0.12em] text-text-muted">{item.label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-3 border-b border-border-subtle pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-border-subtle bg-bg-panel px-3 py-2">
            <Search size={14} className="text-text-muted" />
            <input
              aria-label="Search todos"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search todos"
              className="w-full bg-transparent text-13 text-text-primary outline-none placeholder:text-text-muted"
            />
          </label>
          <label className="flex items-center gap-2 text-12 text-text-muted">
            Sort by
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as TodoSort)}
              className="h-9 rounded-lg border border-border-subtle bg-bg-panel px-2 text-13 text-text-secondary outline-none focus:border-accent-500"
            >
              <option value="priority">Priority</option>
              <option value="due">Due date</option>
              <option value="title">Title</option>
            </select>
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-lg border border-border-subtle bg-bg-panel p-1">
          {(['all', 'open', 'completed'] as TodoStatusFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={cn(
                'rounded-md px-3 py-1.5 text-13 capitalize text-text-secondary transition-colors duration-fast',
                status === s && 'bg-accent-500/15 text-text-primary'
              )}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-border-subtle bg-bg-panel p-1">
          <button
            onClick={() => setPriority('all')}
            className={cn(
              'rounded-md px-3 py-1.5 text-13 text-text-secondary transition-colors duration-fast',
              priority === 'all' && 'bg-accent-500/15 text-text-primary'
            )}
          >
            All priorities
          </button>
          {[1, 2, 3, 4].map((p) => (
            <button
              key={p}
              onClick={() => setPriority(p as Priority)}
              className={cn(
                'rounded-md px-3 py-1.5 text-13 tabular text-text-secondary transition-colors duration-fast',
                priority === p && 'bg-accent-500/15 text-text-primary'
              )}
            >
              P{p}
            </button>
          ))}
        </div>
          <span className="ml-auto text-12 tabular text-text-muted">{visibleCount} shown</span>
        </div>
      </div>

      <div className="space-y-6">
        {isLoading ? (
          <TaskList tasks={undefined} isLoading goalTitles={goalTitles} />
        ) : groups.length === 0 ? (
          <TaskList
            tasks={[]}
            emptyTitle="No tasks match"
            emptyBody="Try a different search or filter."
            goalTitles={goalTitles}
          />
        ) : groups.map((group) => (
          <section key={group.key}>
            <div className="mb-2 flex items-center gap-2">
              <h2 className="text-13 font-semibold uppercase tracking-[0.12em] text-text-secondary">{group.label}</h2>
              <span className="text-12 tabular text-text-muted">{group.tasks.length}</span>
              <span className="h-px flex-1 bg-border-subtle" />
            </div>
            <TaskList tasks={group.tasks} goalTitles={goalTitles} />
          </section>
        ))}
      </div>

      <Dialog open={importOpen} onOpenChange={setImportOpen}>
        <DialogContent>
          <DialogTitle>Create todos from JIRA</DialogTitle>
          <div className="mt-4 space-y-4 text-13 text-text-secondary">
            <div className="rounded-lg border border-border-subtle bg-black/20 p-3">
              <div className="text-text-primary">{jiraPreview.length} local JIRAs match the current preview.</div>
              <div className="mt-1 text-12 text-text-muted">Priority narrows the preview locally. The backend import applies the selected status filter.</div>
            </div>

            <div>
              <div className="mb-2 text-12 uppercase tracking-[0.18em] text-text-muted">Statuses</div>
              <div className="flex flex-wrap gap-2">
                {['Open', 'In Progress', 'Blocked', 'Pending Approval'].map((statusValue) => {
                  const active = importStatuses.includes(statusValue)
                  return (
                    <button
                      key={statusValue}
                      type="button"
                      onClick={() => setImportStatuses((current) => active ? current.filter((item) => item !== statusValue) : [...current, statusValue])}
                      className={cn(
                        'rounded-full border px-2.5 py-1 text-12 transition-colors duration-fast ease-out',
                        active
                          ? 'border-border-strong bg-accent-500/15 text-text-primary'
                          : 'border-border-subtle bg-black/20 text-text-secondary hover:border-border-strong hover:text-text-primary'
                      )}
                    >
                      {statusValue}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <label>
                <div className="mb-1 text-12 uppercase tracking-[0.18em] text-text-muted">Priority</div>
                <select value={importPriority} onChange={(event) => setImportPriority(event.target.value as typeof importPriority)} className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-2 text-13 text-text-primary outline-none focus:border-accent-500">
                  <option value="all">All priorities</option>
                  <option value="Highest">Highest</option>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                  <option value="Lowest">Lowest</option>
                </select>
              </label>
              <label>
                <div className="mb-1 text-12 uppercase tracking-[0.18em] text-text-muted">Mode</div>
                <button
                  type="button"
                  onClick={() => setDryRun((value) => !value)}
                  className={cn(
                    'flex h-9 w-full items-center justify-between rounded-md border px-3 text-13 transition-colors duration-fast ease-out',
                    dryRun
                      ? 'border-border-strong bg-accent-500/15 text-text-primary'
                      : 'border-border-subtle bg-bg-panel text-text-secondary'
                  )}
                >
                  <span>{dryRun ? 'Dry run' : 'Write todos'}</span>
                  <span className="text-12 text-text-muted">{dryRun ? 'Preview only' : 'Create local copies'}</span>
                </button>
              </label>
            </div>

            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={() => setImportOpen(false)}>Cancel</Button>
              <Button type="button" variant="primary" onClick={() => importJira.mutate()} disabled={importJira.isPending}>
                {dryRun ? `Preview ${jiraPreview.length}` : `Import ${jiraPreview.length}`}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
