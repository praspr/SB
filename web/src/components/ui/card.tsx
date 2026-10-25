import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Card — the single elevated-surface primitive.
 * Replaces hand-rolled `rounded-xl border border-border-subtle bg-bg-panel/92`
 * strings. Depth comes from the surface ladder + shadow-card, not alpha washes.
 * Callers add their own padding.
 */
export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('rounded-lg border border-border-subtle bg-surface-1 shadow-card', className)}
        {...props}
      />
    )
  },
)
Card.displayName = 'Card'
