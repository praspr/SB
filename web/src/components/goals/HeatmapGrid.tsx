import type { Goal, GoalHeatmapRow } from '@/lib/goals'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

function truncateTitle(title: string) {
  return title.length > 24 ? `${title.slice(0, 24).trimEnd()}…` : title
}

// Weekly activity scale: a "healthy" goal sees ~7 combined hits/week.
const WEEKLY_MAX = 7

function barTone(count: number) {
  if (count <= 0) return 'bg-surface-sunken'
  if (count < 3) return 'bg-warning-solid/70'
  return 'bg-success-solid/80'
}

export function HeatmapGrid({
  goals,
  heatmap,
}: {
  goals: Goal[]
  heatmap: GoalHeatmapRow[]
}) {
  const byGoal = new Map(heatmap.map((row) => [row.goal_id, row]))
  const maxCount = Math.max(
    WEEKLY_MAX,
    ...goals.map((goal) => {
      const row = byGoal.get(goal.id)
      return (row?.ledger_count ?? 0) + (row?.todo_count ?? 0)
    }),
  )

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <div className="text-14 font-semibold text-text-primary">Weekly activity</div>
        <div className="text-11 uppercase tracking-[0.14em] text-text-muted">last 7 days</div>
      </div>
      <div className="mt-4 space-y-2.5">
        {goals.map((goal) => {
          const row = byGoal.get(goal.id)
          const ledger = row?.ledger_count ?? 0
          const todo = row?.todo_count ?? 0
          const count = ledger + todo
          const width = Math.min(100, (count / maxCount) * 100)
          return (
            <div key={goal.id} className="grid items-center gap-3 md:grid-cols-[180px_1fr_120px]">
              <div className="truncate text-13 text-text-primary" title={goal.title}>
                {truncateTitle(goal.title)}
              </div>
              <div className="h-5 overflow-hidden rounded-md bg-surface-sunken">
                <div
                  className={cn('h-full rounded-md transition-[width] duration-500 ease-out', barTone(count))}
                  style={{ width: `${width}%` }}
                  title={`${ledger} ledger · ${todo} todo`}
                />
              </div>
              <div className="text-right font-mono text-12 tabular text-text-faint">
                {count === 0 ? 'quiet' : `${count} hits`}
              </div>
            </div>
          )
        })}
      </div>
      <div className="mt-4 flex items-center gap-2 border-t border-border-subtle pt-4 text-11 uppercase tracking-[0.14em] text-text-muted">
        <span>Combined ledger + todo hits</span>
        <span className="ml-auto flex items-center gap-1.5 normal-case tracking-normal text-text-faint">
          <span className="h-2 w-2 rounded-full bg-warning-solid/70" /> low
          <span className="ml-2 h-2 w-2 rounded-full bg-success-solid/80" /> healthy
        </span>
      </div>
    </Card>
  )
}
