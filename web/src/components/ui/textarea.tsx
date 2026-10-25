import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Textarea — a styled multi-line input matching the design system (sunken
 * surface, focus ring) so forms read consistently with Input and Select.
 */
export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          'focus-ring w-full rounded-md border border-border-subtle bg-surface-sunken px-3 py-2 text-13 text-text-primary placeholder:text-text-muted shadow-[inset_0_1px_2px_rgba(0,0,0,0.3)] transition-colors duration-fast ease-out focus-visible:border-accent-500',
          className,
        )}
        {...props}
      />
    )
  },
)
Textarea.displayName = 'Textarea'
