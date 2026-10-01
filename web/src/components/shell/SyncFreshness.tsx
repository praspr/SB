import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { syncStatus } from '@/lib/sync-status'
import { useUiStore } from '@/lib/store'
import { cn } from '@/lib/utils'

export function syncFreshnessTone(minutes: number | null) {
  if (minutes == null) return 'muted'
  if (minutes < 15) return 'green'
  if (minutes < 60) return 'amber'
  return 'red'
}

export function minutesSinceLatestSuccess(states: Array<{ last_run_at: string; error: string | null }> | undefined, now = new Date()): number | null {
  const successful = (states ?? []).filter((state) => !state.error && state.last_run_at)
  if (successful.length === 0) return null
  const latest = successful
    .map((state) => new Date(state.last_run_at).getTime())
    .filter((value) => Number.isFinite(value))
    .sort((a, b) => b - a)[0]
  if (!latest) return null
  return Math.max(0, Math.floor((now.getTime() - latest) / 60_000))
}

export function SyncFreshness({ now = new Date() }: { now?: Date }) {
  const setSettingsOpen = useUiStore((s) => s.setSettingsOpen)
  const query = useQuery({
    queryKey: ['sync-status', 'freshness'],
    queryFn: syncStatus,
    staleTime: 30_000,
    retry: 1,
  })

  const minutes = useMemo(() => minutesSinceLatestSuccess(query.data?.states, now), [now, query.data?.states])
  const tone = syncFreshnessTone(minutes)

  const toneClasses =
    tone === 'green'
      ? 'border-success/40 bg-success/10 text-success'
      : tone === 'amber'
        ? 'border-warning/40 bg-warning/10 text-warning'
        : tone === 'red'
          ? 'border-danger/40 bg-danger/10 text-danger'
          : 'border-border-subtle bg-bg-panel text-text-muted'

  return (
    <button
      type="button"
      onClick={() => setSettingsOpen(true)}
      className={cn(
        'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-12 font-medium transition-colors duration-fast ease-out hover:text-text-primary',
        toneClasses,
      )}
      aria-label="Open settings"
      title="Open settings"
    >
      <RefreshCw size={13} className={query.isFetching ? 'animate-spin' : undefined} />
      {minutes == null ? 'Sync unknown' : `${minutes}m since sync`}
    </button>
  )
}
