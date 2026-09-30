import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getGoals, planDay, type DayPlan, type Goals } from '@/lib/plan'

export function TodayView({
  plan,
  goals,
  error,
  planning,
  onPlan,
}: {
  plan?: DayPlan | null
  goals?: Goals
  error?: string
  planning: boolean
  onPlan: () => void
}) {
  const titles = [
    ...(goals?.contractual ?? []),
    ...(goals?.quarterly ?? []),
    ...(goals?.weekly ?? []),
  ]
  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Today</h1>
          <p className="mt-1 text-13 text-text-secondary">Ranked must-dos for the day.</p>
        </div>
        <button type="button" onClick={onPlan} className="rounded-lg border border-border-subtle px-3 py-1.5 text-13">
          {planning ? 'Planning' : 'Plan day'}
        </button>
      </div>
      {error && <p className="text-13 text-danger">{error}</p>}
      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <h2 className="text-14 font-semibold text-text-primary">Plan</h2>
        <pre className="mt-3 whitespace-pre-wrap text-13 text-text-secondary">
          {plan?.plan_md || 'No plan yet.'}
        </pre>
      </section>
      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <h2 className="text-14 font-semibold text-text-primary">Goals</h2>
        {titles.length === 0 ? (
          <p className="mt-2 text-13 text-text-muted">No active goals.</p>
        ) : (
          <ul className="mt-2 space-y-1 text-13 text-text-secondary">
            {titles.map((goal) => (
              <li key={goal.title}>{goal.title}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

export function TodayPage() {
  const client = useQueryClient()
  const goals = useQuery({ queryKey: ['goals'], queryFn: getGoals })
  const plan = useMutation({
    mutationFn: () => planDay(),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['goals'] })
    },
  })
  return (
    <TodayView
      plan={plan.data}
      goals={goals.data}
      error={goals.isError || plan.isError ? 'Could not load today.' : undefined}
      planning={plan.isPending}
      onPlan={() => plan.mutate()}
    />
  )
}
