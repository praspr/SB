import { useQuery } from '@tanstack/react-query'
import { HardDrive } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { ProgressRing } from '@/components/shared/ProgressRing'
import { fetchCoreStatus } from '@/lib/status'
import { formatBytes } from '@/lib/utils'

function tone(percent: number): 'success' | 'warning' | 'danger' {
  if (percent >= 90) return 'danger'
  if (percent >= 70) return 'warning'
  return 'success'
}

/**
 * StorageGauge — computer disk usage as a ProgressRing, with used/total and a
 * health tone. Degrades gracefully to "unavailable" when the backend cannot
 * read disk stats.
 */
export function StorageGauge() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['system', 'status', 'disk'],
    queryFn: fetchCoreStatus,
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: 1,
  })

  const disk = data?.disk ?? null
  const unavailable = isError || (!isLoading && !disk)

  return (
    <Card className="flex items-center gap-4 p-4">
      {disk ? (
        <ProgressRing value={Math.round(disk.percent)} max={100} label="used" tone={tone(disk.percent)} />
      ) : (
        <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full border border-border-subtle text-text-muted">
          <HardDrive size={22} />
        </div>
      )}
      <div className="min-w-0">
        <div className="flex items-center gap-1.5 text-11 uppercase tracking-[0.14em] text-text-muted">
          <HardDrive size={12} />
          Storage
        </div>
        {disk ? (
          <>
            <div className="mt-1 font-mono text-16 tabular text-text-primary">
              {formatBytes(disk.used, 0)} <span className="text-text-faint">/ {formatBytes(disk.total, 0)}</span>
            </div>
            <div className="mt-0.5 text-12 text-text-secondary">{formatBytes(disk.free, 0)} free</div>
          </>
        ) : (
          <div className="mt-1 text-12 text-text-muted">{isLoading ? 'Loading…' : unavailable ? 'Unavailable' : ''}</div>
        )}
      </div>
    </Card>
  )
}
