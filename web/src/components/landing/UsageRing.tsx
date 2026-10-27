import { format } from 'date-fns'
import { ProgressRing } from '@/components/shared/ProgressRing'
import { Card } from '@/components/ui/card'
import { useClaudegateUsage, useCursorUsage } from '@/lib/queries'

function usageTone(percent: number | null): 'accent' | 'warning' | 'danger' {
  if (percent == null) return 'accent'
  if (percent >= 100) return 'danger'
  if (percent >= 80) return 'warning'
  return 'accent'
}

function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-US').format(n)
}

function UsageRingCard({
  label,
  used,
  total,
  remaining,
  plan,
  reset,
  status,
}: {
  label: string
  used: number | null
  total: number | null
  remaining: number | null
  plan: string | null
  reset: string | null
  status?: string
}) {
  const percent = used != null && total != null && total > 0 ? (used / total) * 100 : null

  return (
    <Card className="flex items-center gap-4 p-4">
      <ProgressRing
        value={percent == null ? 0 : Math.round(percent)}
        max={100}
        label={percent == null ? '—' : '%'}
        tone={usageTone(percent)}
      />
      <div className="min-w-0">
        <div className="text-11 uppercase tracking-[0.14em] text-text-muted">{label}</div>
        {percent == null ? (
          <div className="mt-1 text-12 text-text-muted">{status ?? 'Unavailable'}</div>
        ) : (
          <>
            <div className="mt-1 font-mono text-16 tabular text-text-primary">
              {formatNumber(used ?? 0)} <span className="text-text-faint">/ {formatNumber(total ?? 0)}</span>
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-12 text-text-secondary">
              {remaining != null ? <span>{formatNumber(remaining)} left</span> : null}
              {plan ? <span className="text-text-faint">· {plan}</span> : null}
              {reset ? <span className="text-text-faint">· resets {reset}</span> : null}
            </div>
          </>
        )}
      </div>
    </Card>
  )
}

export function ClaudegateUsageRing() {
  const { data, isLoading, isError } = useClaudegateUsage()
  if (isLoading) {
    return <UsageRingCard label="Claudegate" used={null} total={null} remaining={null} plan={null} reset={null} status="Loading…" />
  }
  if (isError || !data) {
    return <UsageRingCard label="Claudegate" used={null} total={null} remaining={null} plan={null} reset={null} status="Unavailable" />
  }
  const { premium, plan, reset_date } = data
  return (
    <UsageRingCard
      label="Claudegate"
      used={premium.used}
      total={premium.total}
      remaining={premium.remaining}
      plan={plan}
      reset={reset_date ? format(new Date(reset_date), 'MMM d') : null}
    />
  )
}

export function CursorUsageRing() {
  const { data, isLoading, isError, error } = useCursorUsage()
  if (isLoading) {
    return <UsageRingCard label="Cursor" used={null} total={null} remaining={null} plan={null} reset={null} status="Loading…" />
  }
  if (isError || !data || data.primaryUsed == null || data.primaryTotal == null) {
    const message = error instanceof Error && error.message.includes('not signed in') ? 'Not signed in' : 'Unavailable'
    return <UsageRingCard label="Cursor" used={null} total={null} remaining={null} plan={null} reset={null} status={message} />
  }
  return (
    <UsageRingCard
      label="Cursor"
      used={data.primaryUsed}
      total={data.primaryTotal}
      remaining={data.primaryTotal - data.primaryUsed}
      plan={data.membershipType}
      reset={data.resetDate ? format(new Date(data.resetDate), 'MMM d') : null}
    />
  )
}
