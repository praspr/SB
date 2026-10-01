import { motion } from 'framer-motion'
import { Check, Clock, Pencil } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Task, Priority } from '@/lib/mock-data'
import { formatDueBadge } from '@/lib/due-format'
import { useToast } from '@/lib/useToast'
import { useUiStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import { useCompleteTask, useUncompleteTask } from '@/lib/queries'

const priorityLabel: Record<Priority, string> = {
  1: 'P1',
  2: 'P2',
  3: 'P3',
  4: 'P4',
}

const priorityClasses: Record<Priority, string> = {
  1: 'bg-danger/15 text-danger border-danger/30',
  2: 'bg-warning/15 text-warning border-warning/30',
  3: 'bg-info/15 text-info border-info/30',
  4: 'bg-neutral-800 text-text-muted border-border-subtle',
}

const domainClasses: Record<Task['domain'], string> = {
  work: 'text-text-secondary',
  learning: 'text-info',
  personal: 'text-success',
}

export function TaskRow({ task, goalTitle }: { task: Task; goalTitle?: string }) {
  const completeTask = useCompleteTask()
  const uncompleteTask = useUncompleteTask()
  const openAddTodo = useUiStore((state) => state.openAddTodo)
  const showToast = useToast((state) => state.show)
  const dueBadge = formatDueBadge(task)

  return (
    <motion.div
      layout
      initial={{ opacity: 1 }}
      animate={{ opacity: task.is_completed ? 0.45 : 1 }}
      transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
      className="group flex min-h-[40px] items-center gap-3 rounded-lg border border-border-subtle bg-bg-panel px-3 py-2 transition-colors duration-fast ease-out hover:border-border-strong hover:bg-bg-elevated"
    >
          <button
            onClick={() => {
              if (task.is_completed) {
                uncompleteTask.mutate(task.id, {
                  onSuccess: () => showToast({ kind: 'success', message: 'Reopened' }),
                })
                return
              }
              completeTask.mutate(task.id, {
                onSuccess: () => showToast({ kind: 'success', message: 'Marked complete' }),
              })
            }}
            className={cn(
              'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors duration-fast',
              task.is_completed
                ? 'border-success bg-success/20 text-success'
                : 'border-border-strong text-transparent hover:border-accent-500'
            )}
            aria-label={task.is_completed ? 'Reopen todo' : 'Mark complete'}
          >
            <Check size={12} strokeWidth={3} />
          </button>

          <span
            className={cn(
              'flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full border px-1.5 text-12 font-semibold tabular',
              priorityClasses[task.priority]
            )}
          >
            {priorityLabel[task.priority]}
          </span>

          <div className="min-w-0 flex-1">
            <div
              className={cn(
                'flex items-center gap-2 truncate text-14 font-medium text-text-primary',
                task.is_completed && 'line-through text-text-muted'
              )}
            >
              {dueBadge?.overdue ? <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-danger" aria-hidden="true" /> : null}
              {task.title}
            </div>
            <div className="mt-0.5 flex items-center gap-2 text-12 text-text-muted">
              <span className={domainClasses[task.domain]}>{task.domain}</span>
              <span>·</span>
              <span>{task.source}</span>
              {task.ref && (
                <>
                  <span>·</span>
                  <span className="tabular">{task.ref}</span>
                </>
              )}
              {goalTitle && (
                <>
                  <span>·</span>
                  <span className="rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 text-text-secondary">
                    {goalTitle}
                  </span>
                </>
              )}
              {task.jira_ref && (
                <>
                  <span>·</span>
                  <Link to={`/jira?q=${encodeURIComponent(task.jira_ref)}`} className="rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 text-text-secondary hover:text-text-primary">
                    {task.jira_ref}
                  </Link>
                </>
              )}
              {task.recurrence_rule && (
                <>
                  <span>·</span>
                  <span className="rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 text-text-secondary">
                    {task.recurrence_rule.replace('FREQ=', '').toLowerCase()}
                  </span>
                </>
              )}
              {dueBadge && (
                <>
                  <span>·</span>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 font-medium tabular',
                      dueBadge.tone === 'danger' && 'font-semibold text-danger',
                      dueBadge.tone === 'warning' && 'text-warning',
                      dueBadge.tone === 'muted' && 'text-text-muted',
                    )}
                  >
                    <Clock size={12} />
                    {dueBadge.text}
                  </span>
                </>
              )}
            </div>
          </div>

          {task.score !== undefined && (
            <span className="shrink-0 rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 font-semibold tabular text-text-secondary">
              {task.score}
            </span>
          )}
          <button
            type="button"
            onClick={() => openAddTodo({ edit: task })}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-12 text-text-muted opacity-0 transition-all duration-fast ease-out hover:bg-bg-elevated hover:text-text-primary group-hover:opacity-100"
            aria-label={`Edit ${task.title}`}
          >
            <Pencil size={12} />
            Edit
          </button>
    </motion.div>
  )
}
