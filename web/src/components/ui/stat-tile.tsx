import * as React from 'react'
import { useEffect } from 'react'
import { useSpring, useTransform, motion, useReducedMotion } from 'framer-motion'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

type StatTone = 'default' | 'accent' | 'success' | 'warning' | 'danger' | 'info'

const valueToneClasses: Record<StatTone, string> = {
  default: 'text-text-primary',
  accent: 'text-accent-300',
  success: 'text-success-fg',
  warning: 'text-warning-fg',
  danger: 'text-danger-fg',
  info: 'text-info-fg',
}

const iconToneClasses: Record<StatTone, string> = {
  default: 'text-text-muted',
  accent: 'text-accent-300',
  success: 'text-success-fg',
  warning: 'text-warning-fg',
  danger: 'text-danger-fg',
  info: 'text-info-fg',
}

/** Animated count-up for numeric values; renders static for strings or reduced-motion. */
function CountUp({ value }: { value: number }) {
  const reduce = useReducedMotion()
  const spring = useSpring(reduce ? value : 0, { stiffness: 90, damping: 20 })
  const display = useTransform(spring, (latest) => Math.round(latest).toLocaleString())

  useEffect(() => {
    spring.set(value)
  }, [spring, value])

  if (reduce) return <>{value.toLocaleString()}</>
  return <motion.span>{display}</motion.span>
}

export type StatTileProps = {
  label: string
  value: number | string
  tone?: StatTone
  icon?: React.ReactNode
  delta?: string
  children?: React.ReactNode
  className?: string
}

/**
 * StatTile — a glanceable hero metric. The number is the design: large, mono,
 * tabular, with an animated count-up entrance. Optional sparkline slot via `children`.
 */
export function StatTile({
  label,
  value,
  tone = 'default',
  icon,
  delta,
  children,
  className,
}: StatTileProps) {
  return (
    <Card className={cn('p-4', className)}>
      <div className="flex items-center gap-2">
        {icon ? <span className={cn('shrink-0', iconToneClasses[tone])}>{icon}</span> : null}
        <span className="text-11 uppercase tracking-[0.14em] text-text-muted">{label}</span>
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className={cn('font-mono text-40 tabular tracking-tight', valueToneClasses[tone])}>
          {typeof value === 'number' ? <CountUp value={value} /> : value}
        </span>
        {delta ? <span className="font-mono text-12 tabular text-text-secondary">{delta}</span> : null}
      </div>
      {children ? <div className="mt-3">{children}</div> : null}
    </Card>
  )
}
