import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTasks } from '@/lib/queries'
import { TaskList } from '@/components/tasks/TaskList'
import { QuickAddInput, type QuickAddInputHandle } from '@/components/tasks/QuickAddInput'
import type { Priority } from '@/lib/mock-data'
import { cn } from '@/lib/utils'
import { useUiStore } from '@/lib/store'

type StatusFilter = 'all' | 'open' | 'completed'

export function TodosPage() {
  const { data: tasks, isLoading } = useTasks()
  const [searchParams] = useSearchParams()
  const requestedStatus = searchParams.get('status')
  const initialStatus: StatusFilter =
    requestedStatus === 'all' || requestedStatus === 'completed' ? requestedStatus : 'open'
  const [status, setStatus] = useState<StatusFilter>(initialStatus)
  const [priority, setPriority] = useState<Priority | 'all'>('all')
  const quickAddRef = useRef<QuickAddInputHandle>(null)
  const focusQuickAddSignal = useUiStore((s) => s.focusQuickAddSignal)

  useEffect(() => {
    if (focusQuickAddSignal > 0) {
      quickAddRef.current?.focus()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusQuickAddSignal])

  const filtered = useMemo(() => {
    if (!tasks) return []
    return tasks
      .filter((t) => (status === 'all' ? true : status === 'open' ? !t.is_completed : t.is_completed))
      .filter((t) => (priority === 'all' ? true : t.priority === priority))
      .sort((a, b) => a.priority - b.priority)
  }, [tasks, status, priority])

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-20 font-semibold text-text-primary">Todos</h1>
        <p className="mt-1 text-13 text-text-secondary">Full task list, filterable by status and priority.</p>
      </div>

      <div className="max-w-lg">
        <QuickAddInput ref={quickAddRef} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-lg border border-border-subtle bg-bg-panel p-1">
          {(['all', 'open', 'completed'] as StatusFilter[]).map((s) => (
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
        <span className="ml-auto text-13 tabular text-text-muted">{filtered.length} tasks</span>
      </div>

      <TaskList
        tasks={filtered}
        isLoading={isLoading}
        emptyTitle="No tasks match"
        emptyBody="Try a different filter combination."
      />
    </div>
  )
}
