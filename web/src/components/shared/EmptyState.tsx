import { Inbox } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ReactNode } from 'react'

export type EmptyStateProps = {
  title: string
  body: string
  actionLabel?: string
  onAction?: () => void
  icon?: ReactNode
}

export function EmptyState({ title, body, actionLabel, onAction, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-border-subtle bg-bg-panel/60 px-6 py-10 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border-subtle bg-bg-elevated text-text-muted">
        {icon ?? <Inbox size={18} />}
      </div>
      <div className="text-14 font-semibold text-text-primary">{title}</div>
      <p className="max-w-xs text-13 text-text-secondary">{body}</p>
      {actionLabel && onAction && (
        <Button variant="secondary" onClick={onAction} className="mt-1">
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
