import type { Goal, GoalHeatmapRow } from '@/lib/goals'

export function DriftAlert({
  goals,
  heatmap,
}: {
  goals: Goal[]
  heatmap: GoalHeatmapRow[]
}) {
  const quiet = goals.filter((goal) => {
    const row = heatmap.find((item) => item.goal_id === goal.id)
    return ((row?.ledger_count ?? 0) + (row?.todo_count ?? 0)) === 0
  })

  if (quiet.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 rounded-lg border border-warning/30 bg-warning/10 p-3 text-13 text-text-secondary">
      <span className="font-medium text-text-primary">Drift alert</span>
      {quiet.map((goal) => (
        <span key={goal.id} className="rounded-full border border-warning/30 px-2.5 py-1 text-12 text-warning">
          {goal.title}
        </span>
      ))}
    </div>
  )
}
