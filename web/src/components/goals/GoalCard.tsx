import type { Goal, GoalHeatmapRow } from '@/lib/goals'

export function GoalCard({
  goal,
  heatmap,
  onEdit,
  onArchive,
}: {
  goal: Goal
  heatmap?: GoalHeatmapRow
  onEdit: (goal: Goal) => void
  onArchive: (goal: Goal) => void
}) {
  const combined = (heatmap?.ledger_count ?? 0) + (heatmap?.todo_count ?? 0)
  const fill = Math.min(100, combined * 14)

  return (
    <div className="w-[320px] shrink-0 rounded-xl border border-border-subtle bg-bg-panel/92 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-12 uppercase tracking-[0.18em] text-text-muted">{goal.tier}</div>
          <h3 className="mt-1 text-14 font-semibold text-text-primary">{goal.title}</h3>
          {goal.description ? <p className="mt-2 text-13 leading-6 text-text-secondary">{goal.description}</p> : null}
        </div>
        <button type="button" onClick={() => onEdit(goal)} className="text-12 text-text-muted hover:text-text-primary">Edit</button>
      </div>

      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-black/30">
        <div className="h-full rounded-full bg-success/70" style={{ width: `${fill}%` }} />
      </div>
      <div className="mt-2 flex items-center justify-between text-12 text-text-muted">
        <span>{combined} hits this week</span>
        <span>{goal.target_date || 'no target date'}</span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {goal.keywords.map((keyword) => (
          <span key={keyword} className="rounded-full border border-border-subtle bg-black/20 px-2.5 py-1 text-12 text-text-secondary">
            {keyword}
          </span>
        ))}
      </div>

      <div className="mt-4 flex justify-end">
        <button type="button" onClick={() => onArchive(goal)} className="text-12 text-text-muted hover:text-text-primary">Archive</button>
      </div>
    </div>
  )
}
