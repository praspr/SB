import type { WebexSpace } from '@/lib/mock-data'
import { formatTime, cn } from '@/lib/utils'
import { Users, Hash, User } from 'lucide-react'

export function SpaceRow({ space }: { space: WebexSpace }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border-subtle bg-bg-panel px-3 py-2.5 transition-colors duration-fast ease-out hover:border-border-strong hover:bg-bg-elevated">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border-subtle bg-black/20 text-text-muted">
        {space.is_dm ? <User size={13} /> : <Hash size={13} />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-13 font-medium text-text-primary">{space.name}</div>
        <div className="flex items-center gap-2 text-12 text-text-muted">
          <span className="flex items-center gap-1">
            <Users size={10} /> {space.members_count}
          </span>
          {space.last_activity ? (
            <>
              <span>·</span>
              <span className="tabular">last active {formatTime(space.last_activity)}</span>
            </>
          ) : null}
        </div>
      </div>
      {space.unread_count > 0 && (
        <span
          className={cn(
            'shrink-0 rounded-full bg-accent-500 px-2 py-0.5 text-[11px] font-semibold tabular text-white'
          )}
        >
          {space.unread_count}
        </span>
      )}
    </div>
  )
}
