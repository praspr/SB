import type { Goal, GoalHeatmapRow } from '@/lib/goals'
import { cn } from '@/lib/utils'

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

  return (
    <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
      <div className="text-14 font-semibold text-text-primary">Heatmap · last 7 days</div>
      <div className="mt-4 space-y-3">
        {goals.map((goal) => {
          const row = byGoal.get(goal.id)
          const count = (row?.ledger_count ?? 0) + (row?.todo_count ?? 0)
          return (
            <div key={goal.id} className="grid items-center gap-3 md:grid-cols-[180px_repeat(7,1fr)_80px]">
              <div className="text-13 text-text-primary">{goal.title}</div>
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
    </section>
  )
}
