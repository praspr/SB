import { AlertTriangle, CalendarClock, CheckCircle2, Circle } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { summarizeTodos } from '@/lib/todo-groups'
import type { Task } from '@/lib/mock-data'

type StatItem = {
  label: string
  value: number
  icon: typeof AlertTriangle
  tone: string
}

/**
 * TodoStats — the shared Overdue / Due today / Open / Completed metric strip.
 * Used on both the landing dashboard and the full Todos page so the two stay
 * visually and numerically consistent.
 */
export function TodoStats({ tasks, today }: { tasks: Task[]; today: string }) {
  const summary = summarizeTodos(tasks, today)
  const items: StatItem[] = [
    { label: 'Overdue', value: summary.overdue, icon: AlertTriangle, tone: 'text-danger-fg' },
    { label: 'Due today', value: summary.today, icon: CalendarClock, tone: 'text-warning-fg' },
    { label: 'Open', value: summary.open, icon: Circle, tone: 'text-accent-300' },
    { label: 'Completed', value: summary.completed, icon: CheckCircle2, tone: 'text-success-fg' },
  ]

  return (
    <Card className="grid grid-cols-2 overflow-hidden p-0 sm:grid-cols-4">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex items-center gap-3 border-b border-border-subtle px-4 py-3 last:border-0 sm:border-b-0 sm:border-r sm:last:border-r-0"
        >
          <item.icon size={16} className={cn('shrink-0', item.tone)} />
          <div>
            <div className={cn('font-mono text-20 tabular leading-none text-text-primary', item.value > 0 && item.tone)}>
              {item.value}
            </div>
            <div className="mt-1 text-11 uppercase tracking-[0.12em] text-text-muted">{item.label}</div>
          </div>
        </div>
      ))}
    </Card>
  )
}
