import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, MessageSquare, RefreshCw } from 'lucide-react'
import {
  summarizeWebexSpace,
  useSyncWebex,
  useWebexAttention,
  useWebexMessages,
  useWebexSpaces,
  useWebexStatus,
} from '@/lib/queries'
import { MessagePreview } from '@/components/webex/MessagePreview'
import { SpaceRow } from '@/components/webex/SpaceRow'
import { EmptyState } from '@/components/shared/EmptyState'
import { SkeletonRow } from '@/components/shared/SkeletonRow'
import { Button } from '@/components/ui/button'

export function WebexPage() {
  const { data: messages, isLoading: messagesLoading, isError, error } = useWebexMessages()
  const { data: spaces, isLoading: spacesLoading } = useWebexSpaces()
  const attention = useWebexAttention()
  const status = useWebexStatus()
  const sync = useSyncWebex()
  const [spaceId, setSpaceId] = useState('')
  const [summary, setSummary] = useState('')
  const [summaryError, setSummaryError] = useState('')

  const dms = useMemo(() => messages?.filter((m) => m.is_dm) ?? [], [messages])
  const mentions = useMemo(() => messages?.filter((m) => m.is_mention) ?? [], [messages])
  const activeSpaces = useMemo(
    () => [...(spaces ?? [])].sort((a, b) => b.unread_count - a.unread_count),
    [spaces],
  )

  async function handleSummarize() {
    setSummaryError('')
    setSummary('')
    try {
      const result = await summarizeWebexSpace(spaceId)
      setSummary(result.summary)
    } catch (err) {
      setSummaryError((err as Error).message)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Webex</h1>
          <p className="mt-1 text-13 text-text-secondary">
            Read-only mirror
            {status.data ? ` · ${status.data.meetings_count} meetings · ${status.data.messages_count} previews` : ''}
          </p>
          {status.data && !status.data.authenticated ? (
            <a
              className="mt-1 inline-block text-13 text-text-secondary underline"
              href="http://127.0.0.1:8787/webex/login"
            >
              Sign in to Webex
            </a>
          ) : null}
          {sync.data?.errors?.length ? (
            <p className="mt-1 text-12 text-text-muted">{sync.data.errors.join(' ')}</p>
          ) : null}
        </div>
        <Button variant="secondary" onClick={() => sync.mutate()} disabled={sync.isPending}>
          {sync.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          Sync
        </Button>
      </div>

      {isError ? (
        <div className="rounded-md border border-danger/40 bg-danger/5 p-3 text-13 text-danger">
          {(error as Error)?.message ?? 'Failed to load Webex'} — is sb running on :8787?
        </div>
      ) : null}

      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-16 font-semibold text-text-primary">Needs attention</h2>
          <Link to="/meetings" className="text-12 text-text-secondary underline">
            Meetings
          </Link>
        </div>
        <div className="mt-4">
          {attention.isLoading ? (
            <SkeletonRow lines={3} />
          ) : (attention.data?.length ?? 0) === 0 ? (
            <EmptyState title="Nothing waiting" body="Mentions, direct messages, and questions show up after a sync." icon={<MessageSquare size={18} />} />
          ) : (
            <div className="space-y-2">
              {attention.data!.map((message) => (
                <MessagePreview key={message.id} message={message} />
              ))}
            </div>
          )}
        </div>
      </section>

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

        <div className="space-y-6">
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
                    <button key={s.id} type="button" className="block w-full text-left" onClick={() => setSpaceId(s.id)}>
                      <SpaceRow space={s} />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>

          <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
            <h2 className="text-16 font-semibold text-text-primary">Space summary</h2>
            <p className="mt-1 text-12 text-text-muted">Cited from mirrored previews. Nothing is sent back to Webex.</p>
            <div className="mt-3 flex gap-2">
              <input
                value={spaceId}
                onChange={(event) => setSpaceId(event.target.value)}
                placeholder="Space id"
                className="min-w-0 flex-1 rounded-md border border-border-subtle bg-black/20 px-2 py-1.5 text-13 text-text-primary"
              />
              <Button variant="secondary" onClick={handleSummarize} disabled={!spaceId}>
                Summarize
              </Button>
            </div>
            {summaryError ? <p className="mt-3 text-13 text-danger">{summaryError}</p> : null}
            {summary ? <pre className="mt-3 whitespace-pre-wrap text-13 text-text-secondary">{summary}</pre> : null}
          </section>
        </div>
      </div>
    </div>
  )
}
