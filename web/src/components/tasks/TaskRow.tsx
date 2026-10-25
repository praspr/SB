import { motion } from 'framer-motion'
import { Check, Clock, Pencil, Repeat } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Task, Priority } from '@/lib/mock-data'
import { formatDueBadge } from '@/lib/due-format'
import { useToast } from '@/lib/useToast'
import { useUiStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import { useCompleteTask, useUncompleteTask } from '@/lib/queries'

// Priority is a color-only left rail on the row, not a chip in the body.
const priorityRail: Record<Priority, string> = {
  1: 'before:bg-danger-solid',
  2: 'before:bg-warning-solid',
  3: 'before:bg-info-solid',
  4: 'before:bg-transparent',
}

const domainClasses: Record<Task['domain'], string> = {
  work: 'text-text-muted',
  learning: 'text-info-fg',
  personal: 'text-success-fg',
}

export function TaskRow({ task, goalTitle }: { task: Task; goalTitle?: string }) {
  const completeTask = useCompleteTask()
  const uncompleteTask = useUncompleteTask()
  const openAddTodo = useUiStore((state) => state.openAddTodo)
  const showToast = useToast((state) => state.show)
  const dueBadge = formatDueBadge(task)
  const showDueChip = dueBadge && (dueBadge.tone === 'danger' || dueBadge.tone === 'warning')

  return (
    <motion.div
      layout
      initial={{ opacity: 1 }}
      animate={{ opacity: task.is_completed ? 0.45 : 1 }}
      transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        'group relative flex min-h-[44px] items-center gap-3 rounded-lg border border-border-subtle bg-surface-1 py-2 pl-4 pr-3 shadow-raised transition-all duration-150 ease-out',
        'before:absolute before:left-0 before:inset-y-1.5 before:w-[3px] before:rounded-full',
        priorityRail[task.priority],
        'hover:-translate-y-px hover:border-border-strong hover:bg-surface-2 hover:shadow-card',
      )}
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
            ? 'border-success-solid bg-success-solid/20 text-success-fg'
            : 'border-border-strong text-transparent hover:border-accent-500',
        )}
        aria-label={task.is_completed ? 'Reopen todo' : 'Mark complete'}
      >
        <motion.span
          key={String(task.is_completed)}
          initial={task.is_completed ? { scale: 0, rotate: -25 } : false}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 600, damping: 22 }}
        >
          <Check size={12} strokeWidth={3} />
        </motion.span>
      </button>

      <div className="min-w-0 flex-1">
        <div
          className={cn(
            'truncate text-14 font-medium text-text-primary',
            task.is_completed && 'line-through text-text-muted',
          )}
        >
          {task.title}
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-12 text-text-muted">
          {task.ref && <span className="font-mono text-text-faint">{task.ref}</span>}
          <span className={domainClasses[task.domain]}>{task.domain}</span>
          {task.jira_ref && (
            <Link
              to={`/jira?q=${encodeURIComponent(task.jira_ref)}`}
              className="font-mono text-text-faint hover:text-text-secondary"
            >
              {task.jira_ref}
            </Link>
          )}
          {goalTitle && <span className="truncate text-text-faint">{goalTitle}</span>}
          {task.recurrence_rule && (
            <span className="inline-flex items-center gap-1 text-text-faint" title={task.recurrence_rule}>
              <Repeat size={11} />
            </span>
          )}
        </div>
      </div>

      {showDueChip && dueBadge ? (
        <span
          className={cn(
            'inline-flex shrink-0 items-center gap-1 rounded-md border px-2 py-0.5 text-12 font-medium tabular',
            dueBadge.tone === 'danger' && 'border-danger-border bg-danger-bg text-danger-fg',
            dueBadge.tone === 'warning' && 'border-warning-border bg-warning-bg text-warning-fg',
          )}
        >
          <Clock size={12} />
          {dueBadge.text}
        </span>
      ) : dueBadge ? (
        <span className="shrink-0 text-12 tabular text-text-faint">{dueBadge.text}</span>
      ) : null}

      {task.score !== undefined && (
        <span className="shrink-0 font-mono text-12 tabular text-text-faint opacity-0 transition-opacity duration-fast group-hover:opacity-100">
          {task.score}
        </span>
      )}
      <button
        type="button"
        onClick={() => openAddTodo({ edit: task })}
        className="focus-ring inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-12 text-text-muted opacity-0 transition-all duration-fast ease-out hover:bg-surface-3 hover:text-text-primary group-hover:opacity-100"
        aria-label={`Edit ${task.title}`}
      >
        <Pencil size={12} />
        Edit
      </button>
    </motion.div>
  )
}
