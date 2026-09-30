import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Target } from 'lucide-react'
import { GoalCard } from '@/components/goals/GoalCard'
import { GoalDialog } from '@/components/goals/GoalDialog'
import { HeatmapGrid } from '@/components/goals/HeatmapGrid'
import { DriftAlert } from '@/components/goals/DriftAlert'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/button'
import { addGoal, archiveGoal, heatmapLastWeek, listGoalsV2, updateGoal, type Goal, type GoalTier } from '@/lib/goals'
import { cn } from '@/lib/utils'

const tiers: GoalTier[] = ['contractual', 'quarterly', 'weekly']

export function GoalsView({
  tier,
  onTier,
  goals,
  heatmap,
  loading,
  error,
  onNew,
  onEdit,
  onArchive,
}: {
  tier: GoalTier
  onTier: (tier: GoalTier) => void
  goals: Goal[]
  heatmap: Awaited<ReturnType<typeof heatmapLastWeek>>
  loading?: boolean
  error?: string
  onNew: () => void
  onEdit: (goal: Goal) => void
  onArchive: (goal: Goal) => void
}) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Goals</h1>
          <p className="mt-1 text-13 text-text-secondary">Track active goals, weekly activity, and areas drifting out of view.</p>
        </div>
        <Button variant="primary" onClick={onNew}>New goal</Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {tiers.map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => onTier(value)}
            className={cn(
              'rounded-lg border px-3 py-2 text-13 capitalize transition-colors duration-fast ease-out',
              tier === value
                ? 'border-border-strong bg-accent-500/15 text-text-primary'
                : 'border-border-subtle bg-black/20 text-text-secondary hover:border-border-strong hover:text-text-primary'
            )}
          >
            {value}
          </button>
        ))}
      </div>

      {error ? <div className="rounded-md border border-danger/40 bg-danger/5 p-3 text-13 text-danger">{error}</div> : null}
      <DriftAlert goals={goals} heatmap={heatmap} />

      {loading ? (
        <div className="flex gap-4 overflow-hidden">
          {Array.from({ length: 3 }).map((_, index) => <div key={index} className="h-56 w-[320px] animate-pulse rounded-xl border border-border-subtle bg-bg-panel" />)}
        </div>
      ) : goals.length === 0 ? (
        <EmptyState title="No goals yet" body="Create a goal to start tracking alignment and recent activity." icon={<Target size={18} />} actionLabel="New goal" onAction={onNew} />
      ) : (
        <div className="space-y-5">
          <div className="flex gap-4 overflow-x-auto pb-1">
            {goals.map((goal) => (
              <GoalCard
                key={goal.id}
                goal={goal}
                heatmap={heatmap.find((row) => row.goal_id === goal.id)}
                onEdit={onEdit}
                onArchive={onArchive}
              />
            ))}
          </div>
          <HeatmapGrid goals={goals} heatmap={heatmap} />
        </div>
      )}
    </div>
  )
}

export function GoalsPage() {
  const client = useQueryClient()
  const [tier, setTier] = useState<GoalTier>('weekly')
  const [editing, setEditing] = useState<Goal | null>(null)
  const [open, setOpen] = useState(false)

  const goals = useQuery({ queryKey: ['goals-v2', tier], queryFn: () => listGoalsV2({ tier, status: 'active' }) })
  const heatmap = useQuery({ queryKey: ['goals-v2', 'heatmap'], queryFn: heatmapLastWeek, staleTime: 30_000 })

  const save = useMutation({
    mutationFn: (input: { id?: number; tier: GoalTier; title: string; description?: string; keywords: string[]; target_date?: string }) =>
      input.id
        ? updateGoal({
            id: input.id,
            tier: input.tier,
            title: input.title,
            description: input.description,
            keywords: input.keywords,
            target_date: input.target_date,
          })
        : addGoal(input),
    onSuccess: () => {
      setOpen(false)
      setEditing(null)
      void client.invalidateQueries({ queryKey: ['goals-v2'] })
    },
  })
  const archive = useMutation({
    mutationFn: (goal: Goal) => archiveGoal(goal.id),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['goals-v2'] })
    },
  })

  const visibleGoals = useMemo(() => goals.data ?? [], [goals.data])
  const heatmapRows = useMemo(() => heatmap.data ?? [], [heatmap.data])

  return (
    <>
      <GoalsView
        tier={tier}
        onTier={setTier}
        goals={visibleGoals}
        heatmap={heatmapRows}
        loading={goals.isLoading || heatmap.isLoading}
        error={goals.isError || heatmap.isError ? 'Could not load goals.' : undefined}
        onNew={() => {
          setEditing(null)
          setOpen(true)
        }}
        onEdit={(goal) => {
          setEditing(goal)
          setOpen(true)
        }}
        onArchive={(goal) => archive.mutate(goal)}
      />
      <GoalDialog
        open={open}
        goal={editing}
        onOpenChange={setOpen}
        onSubmit={(input) => save.mutate(input)}
      />
    </>
  )
}
