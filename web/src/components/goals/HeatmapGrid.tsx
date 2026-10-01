import type { Goal, GoalHeatmapRow } from '@/lib/goals'
import { cn } from '@/lib/utils'

function lastSevenDayLabels() {
  const now = new Date()
  return Array.from({ length: 7 }).map((_, index) => {
    const date = new Date(now)
    date.setDate(now.getDate() - (6 - index))
    return {
      short: date.toLocaleDateString('en-US', { weekday: 'narrow' }),
      full: date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
    }
  })
}

function truncateTitle(title: string) {
  return title.length > 24 ? `${title.slice(0, 24).trimEnd()}…` : title
}

function tone(count: number) {
  if (count <= 0) return 'bg-black/20'
  if (count === 1) return 'bg-success/20'
  if (count === 2) return 'bg-success/35'
  if (count === 3) return 'bg-success/50'
  return 'bg-success/70'
}

export function HeatmapGrid({
  goals,
  heatmap,
}: {
  goals: Goal[]
  heatmap: GoalHeatmapRow[]
}) {
  const byGoal = new Map(heatmap.map((row) => [row.goal_id, row]))
  const columns = lastSevenDayLabels()

  return (
    <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
      <div className="text-14 font-semibold text-text-primary">Heatmap · last 7 days</div>
      <div className="mt-4 overflow-x-auto">
        <div className="grid min-w-[700px] grid-cols-[180px_repeat(7,minmax(0,1fr))_80px] items-end gap-3 pb-2">
          <div />
          {columns.map((column) => (
            <div key={column.full} className="text-center text-11 uppercase tracking-[0.18em] text-text-muted" title={column.full}>
              {column.short}
            </div>
          ))}
          <div />
        </div>
      </div>
      <div className="space-y-3">
        {goals.map((goal) => {
          const row = byGoal.get(goal.id)
          const count = (row?.ledger_count ?? 0) + (row?.todo_count ?? 0)
          return (
            <div key={goal.id} className="grid items-center gap-3 md:grid-cols-[180px_repeat(7,1fr)_80px]">
              <div className="truncate text-13 text-text-primary" title={goal.title}>{truncateTitle(goal.title)}</div>
              {Array.from({ length: 7 }).map((_, index) => (
                <div
                  key={index}
                  className={cn('h-7 rounded-md border border-border-subtle', tone(Math.max(0, count - index)))}
                />
              ))}
              <div className="text-right text-12 text-text-muted">{count} total</div>
            </div>
          )
        })}
      </div>
      <div className="mt-4 border-t border-border-subtle pt-4">
        <div className="text-12 text-text-muted">Combined ledger + todo hits · Last 7 days</div>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-11 uppercase tracking-[0.18em] text-text-muted">Low</span>
          <div className="h-2 flex-1 rounded-full bg-gradient-to-r from-black/20 via-success/35 to-success/70" />
          <span className="text-11 uppercase tracking-[0.18em] text-text-muted">High</span>
        </div>
      </div>
    </section>
  )
}
