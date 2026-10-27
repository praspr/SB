import * as React from 'react'
import { cn } from '@/lib/utils'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger-ghost'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-gradient-to-br from-accent-400 to-accent2-500 text-white border border-accent-500/40 shadow-glow hover:brightness-110 active:scale-[0.97] active:brightness-90',
  secondary:
    'bg-surface-2 text-text-secondary border border-border-subtle hover:border-border-strong hover:text-text-primary active:scale-[0.97]',
  ghost: 'bg-transparent text-text-secondary hover:bg-surface-2 hover:text-text-primary active:scale-[0.97]',
  'danger-ghost': 'bg-transparent text-danger-fg hover:bg-danger-bg active:scale-[0.97]',
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'secondary', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'focus-ring inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-13 font-medium transition-[transform,filter,background-color,border-color,color] duration-fast ease-out disabled:opacity-50 disabled:pointer-events-none',
          variantClasses[variant],
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'
