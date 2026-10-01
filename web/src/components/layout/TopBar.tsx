import { useEffect, useState } from 'react'
import { UsageStats } from '@/components/landing/UsageStats'
import { SyncFreshness } from '@/components/shell/SyncFreshness'
import { formatSystemClock } from '@/lib/system-clock'

export function TopBar({ title, subtitle, now }: { title?: string; subtitle?: string; now?: Date }) {
  const [clock, setClock] = useState(() => now ?? new Date())

  useEffect(() => {
    if (now) return
    const id = window.setInterval(() => setClock(new Date()), 1000)
    return () => window.clearInterval(id)
  }, [now])

  return (
    <header className="sticky top-0 z-20 border-b border-border-subtle bg-bg-app/85 backdrop-blur">
      <div className="grid grid-cols-1 items-center gap-3 px-6 py-3 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:px-8">
        <div className="min-w-0">
          {title ? <h1 className="truncate text-16 font-semibold tracking-tight text-text-primary">{title}</h1> : null}
          {subtitle ? <p className="truncate text-12 text-text-secondary">{subtitle}</p> : null}
        </div>
        <time dateTime={clock.toISOString()} className="justify-self-center text-center text-13 tabular text-text-secondary">
          {formatSystemClock(now ?? clock)}
        </time>
        <div className="flex items-center justify-end gap-2">
          <SyncFreshness now={now ?? clock} />
          <UsageStats compact />
        </div>
      </div>
    </header>
  )
}
