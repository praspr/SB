import type { WebexMessage } from '@/lib/mock-data'
import { initials, formatTime } from '@/lib/utils'
import { MentionBadge } from './MentionBadge'
import { cn } from '@/lib/utils'

export function MessagePreview({ message }: { message: WebexMessage }) {
  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border border-border-subtle bg-bg-panel p-3 transition-colors duration-fast ease-out hover:border-border-strong hover:bg-bg-elevated',
        message.is_unread && 'border-l-2 border-l-accent-500'
      )}
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-800 text-[11px] font-semibold text-text-primary">
        {initials(message.from.name)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-13 font-semibold text-text-primary">{message.from.name}</span>
          <span className="text-12 text-text-muted">in {message.space}</span>
          {message.is_mention && <MentionBadge />}
          <span className="ml-auto shrink-0 text-12 tabular text-text-muted">{formatTime(message.ts)}</span>
        </div>
        <p className="mt-1 truncate text-13 text-text-secondary">{message.preview}</p>
      </div>
      {message.is_unread && <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-accent-500" />}
    </div>
  )
}
