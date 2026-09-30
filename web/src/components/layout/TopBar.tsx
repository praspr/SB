import { useEffect, useState } from 'react'
import { UsageStats } from '@/components/landing/UsageStats'
import { formatSystemClock } from '@/lib/system-clock'
import { useUiStore } from '@/lib/store'

export function TopBar({ title, subtitle, now }: { title: string; subtitle?: string; now?: Date }) {
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen)
  const openAddTodo = useUiStore((s) => s.openAddTodo)
  const [clock, setClock] = useState(() => now ?? new Date())

  useEffect(() => {
    if (now) return
    const id = window.setInterval(() => setClock(new Date()), 1000)
    return () => window.clearInterval(id)
  }, [now])

  return (
    <header className="sticky top-0 z-20 border-b border-border-subtle bg-bg-app/85 backdrop-blur">
      <div className="flex flex-wrap items-center gap-4 px-6 py-3 lg:px-8">
        <div>
          <div className="text-12 uppercase tracking-[0.16em] text-text-muted">sb dashboard</div>
          <div className="mt-1 text-20 font-semibold tracking-tight text-text-primary">{title}</div>
          {subtitle && <div className="mt-0.5 text-13 text-text-secondary">{subtitle}</div>}
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-4">
          <time dateTime={clock.toISOString()} className="text-13 tabular text-text-secondary">
            {formatSystemClock(now ?? clock)}
          </time>
          <UsageStats compact />
          <div className="flex items-center gap-2">
          <button
            onClick={() => openAddTodo()}
            className="hidden items-center gap-2 rounded-lg border border-border-subtle bg-bg-panel px-3 py-2 text-13 text-text-secondary transition hover:border-border-strong hover:text-text-primary md:flex"
          >
            <span className="text-text-muted">⌘N</span>
            <span>Add todo</span>
          </button>
          <button
            onClick={() => setCommandPaletteOpen(true)}
            className="flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-panel px-3 py-2 text-13 text-text-secondary transition hover:border-border-strong hover:text-text-primary"
          >
            <span className="text-text-muted">⌘K</span>
            <span className="hidden sm:inline">Command palette</span>
          </button>
          </div>
        </div>
      </div>
    </header>
  )
}
