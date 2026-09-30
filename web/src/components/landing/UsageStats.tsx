import { format } from 'date-fns'
import { usageArc } from '@/lib/usage-pie'
import { useClaudegateUsage, useCursorUsage } from '@/lib/queries'

function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-US').format(n)
}

export function UsagePie({
  label,
  used,
  total,
  details,
  compact = false,
}: {
  label: string
  used: number | null
  total: number | null
  details: Array<[string, string]>
  compact?: boolean
}) {
  const arc = usageArc(used, total)
  const radius = 15
  const circumference = 2 * Math.PI * radius
  const usedLength = arc.used * circumference
  const percentLabel = arc.percent == null ? 'Usage unavailable' : `${arc.percent.toFixed(1)}% used`
  const tone = arc.percent != null && arc.percent >= 100 ? 'text-danger' : arc.percent != null && arc.percent >= 80 ? 'text-warning' : 'text-accent-500'

  return (
    <div tabIndex={0} className="group relative flex w-fit items-center gap-3 rounded-lg outline-none focus-visible:ring-1 focus-visible:ring-border-strong">
      <svg role="img" aria-label={`${label}, ${percentLabel}`} width={compact ? 28 : 44} height={compact ? 28 : 44} viewBox="0 0 44 44">
        <circle cx="22" cy="22" r={radius} fill="none" className="text-neutral-800" stroke="currentColor" strokeWidth="6" />
        <circle
          cx="22"
          cy="22"
          r={radius}
          fill="none"
          className={tone}
          stroke="currentColor"
          strokeWidth="6"
          strokeDasharray={`${usedLength} ${circumference - usedLength}`}
          transform="rotate(-90 22 22)"
        />
      </svg>
      <div>
        <div className={compact ? 'text-12 font-medium text-text-primary' : 'text-13 font-medium text-text-primary'}>{compact ? label.replace('GitHub ', '') : label}</div>
        <div className="text-12 tabular text-text-muted">{percentLabel}</div>
      </div>
      <div className={`absolute top-full z-30 hidden pt-2 group-hover:block group-focus-within:block ${compact ? 'right-0' : 'left-0'}`}>
        <dl className="w-64 rounded-lg border border-border-subtle bg-bg-elevated p-3">
          {details.map(([name, value]) => (
            <div key={name} className="flex items-baseline justify-between gap-4 py-0.5 text-12">
              <dt className="text-text-muted">{name}</dt>
              <dd className="text-right text-text-primary">{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  )
}

function CopilotPie({ compact = false }: { compact?: boolean }) {
  const { data, isLoading, isError } = useClaudegateUsage()
  if (isLoading) return <UsagePie compact={compact} label="GitHub Copilot" used={null} total={null} details={[['Status', 'Loading']]} />
  if (isError || !data) {
    return <UsagePie compact={compact} label="GitHub Copilot" used={null} total={null} details={[['Status', 'Unavailable'], ['Source', 'claudegate :9999']]} />
  }

  const { premium, plan, reset_date, chat, completions, stale } = data
  return (
    <UsagePie
      compact={compact}
      label="GitHub Copilot"
      used={premium.used}
      total={premium.total}
      details={[
        ['Plan', plan],
        ['Used', `${formatNumber(premium.used)} / ${formatNumber(premium.total)}`],
        ['Remaining', formatNumber(premium.remaining)],
        ['Chat', chat.unlimited ? 'unlimited' : 'limited'],
        ['Completions', completions.unlimited ? 'unlimited' : 'limited'],
        ['Resets', format(new Date(reset_date), 'MMM d')],
        ['Cache', stale ? 'stale' : 'fresh'],
      ]}
    />
  )
}

function CursorPie({ compact = false }: { compact?: boolean }) {
  const { data, isLoading, isError, error } = useCursorUsage()
  if (isLoading) return <UsagePie compact={compact} label="Cursor" used={null} total={null} details={[['Status', 'Loading']]} />
  if (isError || !data) {
    const message = error instanceof Error ? error.message : 'Unavailable'
    return (
      <UsagePie
        compact={compact}
        label="Cursor"
        used={null}
        total={null}
        details={[['Status', message.includes('not signed in') ? 'Not signed in' : 'Unavailable']]}
      />
    )
  }
  if (data.primaryUsed == null || data.primaryTotal == null) {
    return <UsagePie compact={compact} label="Cursor" used={null} total={null} details={[['Status', 'Usage format changed']]} />
  }

  return (
    <UsagePie
      compact={compact}
      label="Cursor"
      used={data.primaryUsed}
      total={data.primaryTotal}
      details={[
        ['Plan', data.membershipType ?? 'unknown'],
        ['Meter', data.primaryLabel],
        ['Used', `${formatNumber(data.primaryUsed)} / ${formatNumber(data.primaryTotal)}`],
        ['Resets', data.resetDate ? format(new Date(data.resetDate), 'MMM d') : 'not reported'],
      ]}
    />
  )
}

export function UsageStats({ compact = false }: { compact?: boolean }) {
  return (
    <section className={compact ? 'flex items-center gap-4' : 'flex flex-wrap items-center gap-8'}>
      <CopilotPie compact={compact} />
      <CursorPie compact={compact} />
    </section>
  )
}
