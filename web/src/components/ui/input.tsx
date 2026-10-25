import * as React from 'react'
import { cn } from '@/lib/utils'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          'focus-ring h-9 w-full rounded-md border border-border-subtle bg-surface-sunken px-3 text-14 text-text-primary placeholder:text-text-muted shadow-[inset_0_1px_2px_rgba(0,0,0,0.3)] transition-colors duration-fast ease-out focus-visible:border-accent-500',
          className
        )}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'
