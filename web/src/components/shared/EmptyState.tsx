import { Inbox, SearchX, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

export type EmptyStateVariant = 'empty' | 'no-results' | 'error'

export type EmptyStateProps = {
  title: string
  body: string
  actionLabel?: string
  onAction?: () => void
  icon?: ReactNode
  variant?: EmptyStateVariant
}

const variantIcon: Record<EmptyStateVariant, ReactNode> = {
  empty: <Inbox size={26} />,
  'no-results': <SearchX size={26} />,
  error: <AlertTriangle size={26} />,
}

const variantTile: Record<EmptyStateVariant, string> = {
  empty: 'bg-accent-500/10 text-accent-300 ring-accent-500/20',
  'no-results': 'bg-info-bg text-info-fg ring-info-border/40',
  error: 'bg-danger-bg text-danger-fg ring-danger-border/40',
}

export function EmptyState({ title, body, actionLabel, onAction, icon, variant = 'empty' }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-border-subtle bg-surface-1 px-6 py-12 text-center shadow-raised">
      <div className="relative">
        <div className={cn('absolute inset-0 rounded-2xl blur-xl opacity-60', variantTile[variant])} aria-hidden />
        <div
          className={cn(
            'relative flex h-16 w-16 items-center justify-center rounded-2xl ring-1',
            variantTile[variant],
          )}
        >
          {icon ?? variantIcon[variant]}
        </div>
      </div>
      <div className="text-16 font-semibold text-text-primary">{title}</div>
      <p className="max-w-sm text-13 text-text-secondary">{body}</p>
      {actionLabel && onAction && (
        <Button variant={variant === 'empty' ? 'primary' : 'secondary'} onClick={onAction} className="mt-1">
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
