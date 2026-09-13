import { useMemo } from 'react'
import { useWebexMessages, useWebexSpaces } from '@/lib/queries'
import { MessagePreview } from '@/components/webex/MessagePreview'
import { SpaceRow } from '@/components/webex/SpaceRow'
import { EmptyState } from '@/components/shared/EmptyState'
import { SkeletonRow } from '@/components/shared/SkeletonRow'
import { MessageSquare } from 'lucide-react'

export function WebexPage() {
  const { data: messages, isLoading: messagesLoading } = useWebexMessages()
  const { data: spaces, isLoading: spacesLoading } = useWebexSpaces()

  const dms = useMemo(() => messages?.filter((m) => m.is_dm) ?? [], [messages])
  const mentions = useMemo(() => messages?.filter((m) => m.is_mention) ?? [], [messages])
  const activeSpaces = useMemo(
    () => [...(spaces ?? [])].sort((a, b) => b.unread_count - a.unread_count),
    [spaces]
  )

  return (
    <div className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
      <div className="space-y-6">
        <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-16 font-semibold text-text-primary">Direct messages</h2>
            <span className="rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 tabular text-text-muted">
              {dms.length}
            </span>
          </div>
          <div className="mt-4">
            {messagesLoading ? (
              <SkeletonRow lines={3} />
            ) : dms.length === 0 ? (
              <EmptyState title="No DMs" body="No recent direct messages." icon={<MessageSquare size={18} />} />
            ) : (
              <div className="space-y-2">
                {dms.map((m) => (
                  <MessagePreview key={m.id} message={m} />
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-16 font-semibold text-text-primary">@Mentions</h2>
            <span className="rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 tabular text-text-muted">
              {mentions.length}
            </span>
          </div>
          <div className="mt-4">
            {messagesLoading ? (
              <SkeletonRow lines={3} />
            ) : mentions.length === 0 ? (
              <EmptyState title="No mentions" body="You're not mentioned anywhere recently." icon={<MessageSquare size={18} />} />
            ) : (
              <div className="space-y-2">
                {mentions.map((m) => (
                  <MessagePreview key={m.id} message={m} />
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-16 font-semibold text-text-primary">Spaces</h2>
          <span className="rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 tabular text-text-muted">
            {activeSpaces.length}
          </span>
        </div>
        <div className="mt-4">
          {spacesLoading ? (
            <SkeletonRow lines={5} />
          ) : activeSpaces.length === 0 ? (
            <EmptyState title="No spaces" body="No spaces with recent activity." icon={<MessageSquare size={18} />} />
          ) : (
            <div className="space-y-2">
              {activeSpaces.map((s) => (
                <SpaceRow key={s.id} space={s} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
