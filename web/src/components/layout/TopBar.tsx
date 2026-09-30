import { useEffect, useState } from 'react'
import { UsageStats } from '@/components/landing/UsageStats'
import { formatSystemClock } from '@/lib/system-clock'

export function TopBar({ now }: { now?: Date }) {
  const [clock, setClock] = useState(() => now ?? new Date())

  useEffect(() => {
    if (now) return
    const id = window.setInterval(() => setClock(new Date()), 1000)
    return () => window.clearInterval(id)
  }, [now])

  return (
    <header className="sticky top-0 z-20 border-b border-border-subtle bg-bg-app/85 backdrop-blur">
      <div className="grid grid-cols-1 items-center gap-3 px-6 py-3 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:px-8">
        <div className="hidden md:block" />
        <time dateTime={clock.toISOString()} className="justify-self-center text-center text-13 tabular text-text-secondary">
          {formatSystemClock(now ?? clock)}
        </time>
        <div className="flex justify-end">
          <UsageStats compact />
        </div>
      </div>
    </header>
  )
}
