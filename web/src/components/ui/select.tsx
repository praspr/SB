import * as React from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Select — a styled wrapper around a native <select> matching the design
 * system (sunken surface, focus ring, chevron affordance). Keeps the native
 * element for accessibility and keyboard behavior.
 */
export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => {
    return (
      <div className="relative">
        <select
          ref={ref}
          className={cn(
            'focus-ring h-9 w-full appearance-none rounded-md border border-border-subtle bg-surface-sunken pl-3 pr-8 text-13 text-text-primary shadow-[inset_0_1px_2px_rgba(0,0,0,0.3)] transition-colors duration-fast ease-out focus-visible:border-accent-500',
            className,
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown
          size={14}
          className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted"
        />
      </div>
    )
  },
)
Select.displayName = 'Select'
