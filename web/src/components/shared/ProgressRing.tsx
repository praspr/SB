import { cn } from '@/lib/utils'

/**
 * ProgressRing — a dependency-free SVG arc for showing a count or percentage.
 * Depth comes from a quiet track ring + a saturated progress arc, with the
 * value rendered large and mono in the center.
 */
export function ProgressRing({
  value,
  max,
  label,
  size = 64,
  stroke = 6,
  tone = 'accent',
  className,
}: {
  value: number
  max: number
  label?: string
  size?: number
  stroke?: number
  tone?: 'accent' | 'success' | 'warning' | 'danger' | 'info'
  className?: string
}) {
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const fraction = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0
  const dash = fraction * circumference

  const toneClass = {
    accent: 'text-accent-400',
    success: 'text-success-fg',
    warning: 'text-warning-fg',
    danger: 'text-danger-fg',
    info: 'text-info-fg',
  }[tone]

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} className="text-surface-sunken" stroke="currentColor" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          className={cn(toneClass, 'transition-[stroke-dasharray] duration-500 ease-out')}
          stroke="currentColor"
          strokeDasharray={`${dash} ${circumference - dash}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-16 tabular leading-none text-text-primary">{value}</span>
        {label ? <span className="mt-0.5 text-11 text-text-faint">{label}</span> : null}
      </div>
    </div>
  )
}
