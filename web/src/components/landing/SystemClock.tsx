import { useEffect, useState } from 'react'
import { Card } from '@/components/ui/card'

/**
 * SystemClock — a glanceable day-of-week / date / live time block for the
 * landing health strip. Updates every second (reduced-motion unaffected since
 * it's a text update, not an animation).
 */
export function SystemClock({ now }: { now?: Date }) {
  const [clock, setClock] = useState(() => now ?? new Date())

  useEffect(() => {
    if (now) return
    const id = window.setInterval(() => setClock(new Date()), 1000)
    return () => window.clearInterval(id)
  }, [now])

  const value = now ?? clock
  const weekday = value.toLocaleDateString('en-US', { weekday: 'long' })
  const date = value.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
  const time = value.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit' })

  return (
    <Card className="flex flex-col justify-center p-4">
      <div className="text-11 uppercase tracking-[0.14em] text-text-muted">{weekday}</div>
      <time dateTime={value.toISOString()} className="mt-1 font-mono text-32 tabular tracking-tight text-text-primary">
        {time}
      </time>
      <div className="mt-1 text-12 text-text-secondary">{date}</div>
    </Card>
  )
}
