import { format } from 'date-fns'
import { useClaudegateUsage, useCursorUsage } from '@/lib/queries'
import { cn } from '@/lib/utils'

function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-US').format(n)
}

function TileShell({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('rounded-lg border border-neutral-800 bg-neutral-900 p-4', className)}>
      {children}
    </div>
  )
}

function TileHeader({ label, tag, tagTone = 'default' }: { label: string; tag: string; tagTone?: 'default' | 'muted' }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-12 text-text-muted">{label}</span>
      <span
        className={cn(
          'rounded-full border px-2 py-0.5 text-[11px] font-medium',
          tagTone === 'default'
            ? 'border-accent-700 bg-accent-800/40 text-accent-200'
            : 'border-neutral-700 bg-neutral-800/60 text-neutral-500'
        )}
      >
        {tag}
      </span>
    </div>
  )
}

function CopilotTile() {
  const { data, isLoading, isError } = useClaudegateUsage()

  if (isError) {
    return (
      <TileShell className="border-danger/40">
        <TileHeader label="GitHub Copilot" tag="via claudegate" />
        <div className="mt-4 text-13 text-danger">Unavailable</div>
        <p className="mt-1 text-[11px] text-text-muted">Couldn't reach claudegate at :9999.</p>
      </TileShell>
    )
  }

  if (isLoading || !data) {
    return (
      <TileShell>
        <TileHeader label="GitHub Copilot" tag="via claudegate" />
        <div className="mt-4 h-7 w-40 animate-pulse rounded bg-neutral-800" />
        <div className="mt-3 h-1 w-full animate-pulse rounded-full bg-neutral-800" />
        <div className="mt-3 h-3 w-32 animate-pulse rounded bg-neutral-800" />
      </TileShell>
    )
  }

  const { premium, plan, reset_date, chat, completions } = data
  const percent = Math.min(100, Math.max(0, premium.percent_used))

  return (
    <TileShell>
      <TileHeader label="GitHub Copilot" tag="via claudegate" />
      <div className="mt-1 text-[11px] capitalize text-text-secondary">{plan} plan</div>

      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold tabular-nums text-text-primary">
          {formatNumber(premium.used)}
        </span>
        <span className="text-13 tabular-nums text-text-muted">/ {formatNumber(premium.total)}</span>
      </div>

      <div className="mt-2 h-1 w-full rounded-full bg-neutral-800">
        <div
          className="h-1 rounded-full bg-accent-500"
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="mt-1 text-[11px] tabular-nums text-text-muted">{premium.percent_used}% used</div>

      <div className="mt-3 flex items-center justify-between text-xs text-text-muted">
        <span>Resets {format(new Date(reset_date), 'MMM d')}</span>
        <span>
          chat: {chat.unlimited ? 'unlimited' : 'limited'} · completions:{' '}
          {completions.unlimited ? 'unlimited' : 'limited'}
        </span>
      </div>
    </TileShell>
  )
}

function CursorTile() {
  const { data, isLoading, isError, error, refetch } = useCursorUsage()

  if (isLoading) {
    return (
      <TileShell>
        <TileHeader label="Cursor" tag="loading" tagTone="muted" />
        <div className="mt-4 h-7 w-40 animate-pulse rounded bg-neutral-800" />
        <div className="mt-3 h-1 w-full animate-pulse rounded-full bg-neutral-800" />
        <div className="mt-3 h-3 w-32 animate-pulse rounded bg-neutral-800" />
      </TileShell>
    )
  }

  if (isError) {
    const message = error instanceof Error ? error.message : 'Unknown error'
    const notSignedIn = message.includes('not signed in')

    if (notSignedIn) {
      return (
        <TileShell>
          <TileHeader label="Cursor" tag="Not signed in" tagTone="muted" />
          <p className="mt-4 text-13 leading-5 text-text-muted">
            Sign in to the Cursor app to see usage.
          </p>
          <button
            onClick={() => refetch()}
            className="mt-4 rounded-md border border-neutral-700 bg-neutral-800/60 px-3 py-1.5 text-13 text-text-secondary transition hover:border-neutral-600 hover:text-text-primary"
          >
            Retry
          </button>
        </TileShell>
      )
    }

    return (
      <TileShell className="border-danger/40">
        <TileHeader label="Cursor" tag="Error" />
        <div className="mt-4 text-13 text-danger">Unavailable</div>
        <p className="mt-1 text-[11px] text-text-muted">{message}</p>
      </TileShell>
    )
  }

  if (!data) return null

  const { membershipType, primaryUsed, primaryTotal, primaryPercent, primaryLabel, resetDate, raw } = data

  if (primaryUsed == null || primaryTotal == null) {
    return (
      <TileShell>
        <TileHeader label="Cursor" tag={membershipType ?? 'unknown plan'} />
        <p className="mt-4 text-13 leading-5 text-text-muted">Format changed — showing raw</p>
        <button
          onClick={() => console.log('[cursor] raw usage payload:', raw)}
          className="mt-3 text-[11px] text-accent-300 underline decoration-neutral-700 underline-offset-2 hover:text-accent-200"
        >
          Log raw JSON to console
        </button>
      </TileShell>
    )
  }

  const percent = Math.min(100, Math.max(0, primaryPercent ?? 0))

  return (
    <TileShell>
      <TileHeader label="Cursor" tag={membershipType ?? 'plan'} />
      {membershipType && <div className="mt-1 text-[11px] capitalize text-text-secondary">{membershipType} plan</div>}

      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold tabular-nums text-text-primary">
          {formatNumber(primaryUsed)}
        </span>
        <span className="text-13 tabular-nums text-text-muted">/ {formatNumber(primaryTotal)}</span>
      </div>

      <div className="mt-2 h-1 w-full rounded-full bg-neutral-800">
        <div className="h-1 rounded-full bg-accent-500" style={{ width: `${percent}%` }} />
      </div>
      <div className="mt-1 text-[11px] tabular-nums text-text-muted">{percent.toFixed(1)}% used</div>

      <div className="mt-3 flex items-center justify-between text-xs text-text-muted">
        <span>{resetDate ? `Resets ${format(new Date(resetDate), 'MMM d')}` : primaryLabel}</span>
        {resetDate && <span>{primaryLabel}</span>}
      </div>
    </TileShell>
  )
}

export function UsageStats() {
  return (
    <section className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2">
      <CopilotTile />
      <CursorTile />
    </section>
  )
}
