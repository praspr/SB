import * as React from 'react'
import { cn } from '@/lib/utils'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          'h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-3 text-14 text-text-primary placeholder:text-text-muted outline-none transition-colors duration-fast ease-out focus:border-accent-500 focus:ring-1 focus:ring-accent-500',
          className
        )}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'
