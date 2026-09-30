import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { fetchCoreStatus, statusPhase, type CoreStatus } from '@/lib/status'
import { cn } from '@/lib/utils'

export type StatusViewProps = {
  phase: 'connected' | 'degraded' | 'loading'
  data?: CoreStatus
  detail?: string
  refreshedLabel: string
  onRetry: () => void
}

export function StatusView({ phase, data, detail, refreshedLabel, onRetry }: StatusViewProps) {
  const connected = phase === 'connected'
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Status</h1>
          <p className="mt-1 text-13 text-text-secondary">
            Local sb MCP readiness. No credentials are shown.
          </p>
        </div>
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-panel px-3 py-1.5 text-13 text-text-secondary hover:text-text-primary"
        >
          <RefreshCw size={14} />
          Retry
        </button>
      </div>

      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'h-2.5 w-2.5 rounded-full',
              phase === 'loading' && 'bg-text-muted',
              connected && 'bg-success',
              phase === 'degraded' && 'bg-danger',
            )}
          />
          <h2 className="text-16 font-semibold capitalize text-text-primary">{phase}</h2>
        </div>
        {detail && <p className="mt-3 text-13 text-text-secondary">{detail}</p>}
        <dl className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Database</dt>
            <dd className="mt-1 text-14 text-text-primary">
              {data ? (data.database.ready ? 'ready' : 'not ready') : 'unknown'}
            </dd>
          </div>
          <div>
            <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Schema version</dt>
            <dd className="mt-1 text-14 tabular text-text-primary">
              {data?.database.schema_version ?? '—'}
            </dd>
          </div>
          <div>
            <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Service</dt>
            <dd className="mt-1 text-14 text-text-primary">{data?.version ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Last refresh</dt>
            <dd className="mt-1 text-14 text-text-primary">{refreshedLabel}</dd>
          </div>
        </dl>
        <div className="mt-4 flex flex-wrap gap-2 text-13 text-text-secondary">
          <span className="rounded-full border border-border-subtle px-2.5 py-1">
            tools {data?.counts.tools ?? '—'}
          </span>
          <span className="rounded-full border border-border-subtle px-2.5 py-1">
            prompts {data?.counts.prompts ?? '—'}
          </span>
          <span className="rounded-full border border-border-subtle px-2.5 py-1">
            resources {data?.counts.resources ?? '—'}
          </span>
        </div>
      </section>
    </div>
  )
}

export function StatusPage() {
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null)
  const query = useQuery({
    queryKey: ['core-status'],
    queryFn: async () => {
      const data = await fetchCoreStatus()
      setRefreshedAt(new Date())
      return data
    },
    retry: 1,
  })

  const phase = query.isPending
    ? 'loading'
    : statusPhase(query.data, query.isError)

  return (
    <StatusView
      phase={phase}
      data={query.data}
      detail={query.isError ? 'MCP is unreachable or returned an error.' : undefined}
      refreshedLabel={refreshedAt ? refreshedAt.toLocaleString() : 'not yet'}
      onRetry={() => {
        void query.refetch()
      }}
    />
  )
}
