import type { Goal, GoalHeatmapRow } from '@/lib/goals'
import { Card } from '@/components/ui/card'
import { ProgressRing } from '@/components/shared/ProgressRing'

// Weekly activity target used to scale the ring (hits toward a "healthy" week).
const WEEKLY_TARGET = 7

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
  const tone = combined === 0 ? 'danger' : combined < 3 ? 'warning' : 'success'

  return (
    <Card className="w-[320px] shrink-0 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-11 uppercase tracking-[0.14em] text-text-muted">{goal.tier}</div>
          <h3 className="mt-1 text-14 font-semibold text-text-primary">{goal.title}</h3>
          {goal.description ? <p className="mt-2 text-13 leading-6 text-text-secondary">{goal.description}</p> : null}
        </div>
        <button type="button" onClick={() => onEdit(goal)} className="focus-ring rounded text-12 text-text-muted hover:text-text-primary">
          Edit
        </button>
      </div>

      <div className="mt-4 flex items-center gap-4">
        <ProgressRing value={combined} max={WEEKLY_TARGET} label="hits" tone={tone} />
        <div className="min-w-0 text-12 text-text-muted">
          <div className="text-text-secondary">{combined} hits this week</div>
          <div className="mt-1 font-mono text-text-faint">{goal.target_date || 'no target date'}</div>
        </div>
      </div>

      {goal.keywords.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {goal.keywords.map((keyword) => (
            <span key={keyword} className="rounded-md bg-surface-sunken px-2 py-0.5 text-12 text-text-faint">
              {keyword}
            </span>
          ))}
        </div>
      )}

      <div className="mt-4 flex justify-end">
        <button type="button" onClick={() => onArchive(goal)} className="focus-ring rounded text-12 text-text-muted hover:text-text-primary">
          Archive
        </button>
      </div>
    </Card>
  )
}
