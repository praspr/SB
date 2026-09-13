import * as React from 'react'
import { cn } from '@/lib/utils'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger-ghost'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-accent-500 text-white border border-border-strong hover:brightness-110',
  secondary:
    'bg-bg-panel text-text-secondary border border-border-subtle hover:border-border-strong hover:text-text-primary',
  ghost: 'bg-transparent text-text-secondary hover:bg-bg-elevated hover:text-text-primary',
  'danger-ghost': 'bg-transparent text-danger hover:bg-danger/10',
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'secondary', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-13 font-medium transition-colors duration-fast ease-out disabled:opacity-50 disabled:pointer-events-none',
          variantClasses[variant],
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'
