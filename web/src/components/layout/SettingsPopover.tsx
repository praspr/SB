import { useState, type ReactNode } from 'react'
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Loader2, RefreshCw, X } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { SETTING_CHECKS, type CheckResult } from '@/lib/settings-checks'
import { fetchCoreStatus } from '@/lib/status'
import { cn } from '@/lib/utils'

type SettingsPopoverProps = {
  children: ReactNode
}

export function SettingsPopover({ children }: SettingsPopoverProps) {
  const queryClient = useQueryClient()
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null)

  const checks = useQueries({
    queries: SETTING_CHECKS.map((check) => ({
      queryKey: ['setting-check', check.id],
      queryFn: check.fn,
      staleTime: 15_000,
      retry: 0,
    })),
  })

  const coreStatusQuery = useQuery({
    queryKey: ['core-status'],
    queryFn: async () => {
      const data = await fetchCoreStatus()
      setRefreshedAt(new Date())
      return data
    },
    staleTime: 15_000,
    retry: 0,
  })

  const rows = SETTING_CHECKS.map((check, index) => {
    const query = checks[index]
    const data = query.data

    if (query.isPending || !data) {
      return {
        name: check.id,
        label: check.label,
        status: 'loading',
        subtext: undefined,
      } satisfies CheckResult
    }

    return data
  })

  const isRefreshing = checks.some((query) => query.isFetching) || coreStatusQuery.isFetching

  return (
    <Popover>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent
        side="right"
        align="end"
        collisionPadding={12}
        className="w-[340px] rounded-xl border-border-strong bg-bg-panel p-4"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-14 font-semibold text-text-primary">Settings</h2>
            <button
              type="button"
              aria-label="Refresh settings checks"
              onClick={() => {
                void queryClient.invalidateQueries({ queryKey: ['setting-check'] })
                void queryClient.invalidateQueries({ queryKey: ['core-status'] })
              }}
              className="inline-flex items-center justify-center rounded-md border border-border-subtle p-1.5 text-text-muted transition-colors duration-fast ease-out hover:border-border-strong hover:text-text-primary"
            >
              <RefreshCw size={14} className={cn(isRefreshing && 'animate-spin')} />
            </button>
          </div>

          <section className="space-y-2.5">
            <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Connections</div>
            <div className="space-y-1.5">
              {rows.map((row) => (
                <div
                  key={row.name}
                  className="flex items-start gap-3 rounded-lg border border-border-subtle bg-black/20 px-3 py-2.5"
                >
                  <div className="flex h-[18px] w-[18px] shrink-0 items-center justify-center pt-0.5">
                    {row.status === 'loading' && <Loader2 size={16} className="animate-spin text-text-muted" />}
                    {row.status === 'ok' && <Check size={16} className="text-success" />}
                    {row.status === 'fail' && <X size={16} className="text-danger" />}
                    {row.status === 'unknown' && <span className="h-2 w-2 rounded-full bg-text-muted" />}
                  </div>
                  <div className="min-w-0">
                    <div className="text-13 text-text-primary">{row.label}</div>
                    {row.subtext && <div className="mt-0.5 text-12 text-text-muted">{row.subtext}</div>}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-2.5">
            <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Diagnostics</div>
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Database</dt>
                <dd className="mt-1 text-14 text-text-primary">
                  {coreStatusQuery.data ? (coreStatusQuery.data.database.ready ? 'ready' : 'not ready') : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Schema version</dt>
                <dd className="mt-1 text-14 text-text-primary">
                  {coreStatusQuery.data?.database.schema_version ?? '—'}
                </dd>
              </div>
              <div>
                <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Service version</dt>
                <dd className="mt-1 text-14 text-text-primary">{coreStatusQuery.data?.version ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Last refresh</dt>
                <dd className="mt-1 text-14 text-text-primary">{refreshedAt ? refreshedAt.toLocaleString() : 'not yet'}</dd>
              </div>
            </dl>
            <div className="flex flex-wrap gap-2 text-13 text-text-secondary">
              <span className="rounded-full border border-border-subtle px-2.5 py-1">
                tools {coreStatusQuery.data?.counts.tools ?? '—'}
              </span>
              <span className="rounded-full border border-border-subtle px-2.5 py-1">
                prompts {coreStatusQuery.data?.counts.prompts ?? '—'}
              </span>
              <span className="rounded-full border border-border-subtle px-2.5 py-1">
                resources {coreStatusQuery.data?.counts.resources ?? '—'}
              </span>
            </div>
          </section>

          <div className="text-12 text-text-muted">Local sb MCP readiness. No credentials are shown.</div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
