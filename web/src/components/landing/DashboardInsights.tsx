import { Link } from 'react-router-dom'
import type { JiraTicket, Task } from '@/lib/mock-data'
import type { SignalRecord } from '@/lib/signals'

type Datum = { label: string; value: number }
type DashboardSummary = { todos: Datum[]; jira: Datum[]; signals: Datum[] }

const tones = [
  'bg-accent-500',
  'bg-info',
  'bg-warning',
  'bg-success',
  'bg-danger',
  'bg-purple-400',
  'bg-cyan-400',
  'bg-orange-400',
]

function countBy(values: string[]): Datum[] {
  const counts = new Map<string, number>()
  values.forEach((value) => counts.set(value || 'Unknown', (counts.get(value || 'Unknown') ?? 0) + 1))
  return [...counts].map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value)
}

export function summarizeDashboard(
  tasks: Task[] = [],
  tickets: JiraTicket[] = [],
  signals: SignalRecord[] = [],
): DashboardSummary {
  return {
    todos: [
      { label: 'Open', value: tasks.filter((task) => !task.is_completed).length },
      { label: 'Completed', value: tasks.filter((task) => task.is_completed).length },
    ],
    jira: countBy(tickets.map((ticket) => ticket.status)),
    signals: countBy(signals.map((signal) => signal.source)),
  }
}

function MiniChart({
  title,
  subtitle,
  data,
  href,
}: {
  title: string
  subtitle: string
  data: Datum[]
  href: (label: string) => string
}) {
  const total = data.reduce((sum, item) => sum + item.value, 0)
  const max = Math.max(1, ...data.map((item) => item.value))
  return (
    <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-14 font-semibold text-text-primary">{title}</h3>
          <p className="mt-0.5 text-11 text-text-muted">{subtitle}</p>
        </div>
        <span className="text-20 font-semibold tabular-nums text-text-primary">{total}</span>
      </div>
      <div className="mt-4 flex h-2 overflow-hidden rounded-full bg-neutral-800">
        {data.map((item, index) =>
          item.value > 0 ? (
            <Link
              key={item.label}
              to={href(item.label)}
              aria-label={`${item.label}: ${item.value}`}
              title={`${item.label}: ${item.value}`}
              className={tones[index % tones.length]}
              style={{ width: `${(item.value / Math.max(total, 1)) * 100}%` }}
            />
          ) : null,
        )}
      </div>
      <div className="mt-4 space-y-2">
        {data.slice(0, 6).map((item, index) => (
          <Link key={item.label} to={href(item.label)} className="group flex items-center gap-2 text-12">
            <span className={`h-2 w-2 rounded-full ${tones[index % tones.length]}`} />
            <span className="w-24 truncate text-text-secondary group-hover:text-text-primary">{item.label}</span>
            <span className="h-1 flex-1 overflow-hidden rounded bg-neutral-800">
              <span
                className={`block h-full rounded ${tones[index % tones.length]}`}
                style={{ width: `${(item.value / max) * 100}%` }}
              />
            </span>
            <span className="w-6 text-right tabular-nums text-text-muted">{item.value}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}

export function DashboardInsights({
  tasks,
  tickets,
  signals,
}: {
  tasks?: Task[]
  tickets?: JiraTicket[]
  signals?: SignalRecord[]
}) {
  const summary = summarizeDashboard(tasks, tickets, signals)
  return (
    <section>
      <div className="mb-3">
        <h2 className="text-xs uppercase tracking-wide text-neutral-500">Work pulse</h2>
        <p className="mt-1 text-12 text-text-muted">Click a segment to inspect the underlying records.</p>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <MiniChart
          title="Todos"
          subtitle="Current completion split"
          data={summary.todos}
          href={(label) => `/todos?status=${label.toLowerCase()}`}
        />
        <MiniChart
          title="JIRA status"
          subtitle="Assigned local mirror"
          data={summary.jira}
          href={(label) => `/jira?status=${encodeURIComponent(label)}`}
        />
        <MiniChart
          title="Signals"
          subtitle="Evidence by source"
          data={summary.signals}
          href={(label) => `/signals?source=${encodeURIComponent(label)}`}
        />
      </div>
    </section>
  )
}
