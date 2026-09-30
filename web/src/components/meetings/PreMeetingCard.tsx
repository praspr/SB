import { useMemo } from 'react'
import { Button } from '@/components/ui/button'
import type { PreMeetingContext } from '@/lib/triage'
import { formatTime } from '@/lib/utils'

export function PreMeetingCard({
  context,
  onDismiss,
}: {
  context: PreMeetingContext
  onDismiss: () => void
}) {
  const attendees = context.meeting.attendees ?? []
  const ledger = useMemo(() => context.recent_ledger.slice(0, 5), [context.recent_ledger])

  return (
    <section className="rounded-xl border border-border-strong bg-bg-panel/92 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Pre-meeting context</div>
          <h2 className="mt-1 text-16 font-semibold text-text-primary">{context.meeting.title || 'Upcoming meeting'}</h2>
          <div className="mt-1 text-13 text-text-secondary">
            {context.meeting.start_at ? formatTime(context.meeting.start_at) : 'soon'}
            {context.meeting.end_at ? ` – ${formatTime(context.meeting.end_at)}` : ''}
          </div>
        </div>
        <div className="flex gap-2">
          {context.meeting.join_url ? (
            <a
              href={context.meeting.join_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center rounded-md border border-border-strong bg-accent-500 px-3 py-2 text-13 font-medium text-white transition hover:brightness-110"
            >
              Join
            </a>
          ) : null}
          <Button variant="ghost" onClick={onDismiss}>Dismiss</Button>
        </div>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg border border-border-subtle bg-black/20 p-4">
          <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Meeting</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {attendees.map((attendee) => (
              <span key={attendee.email || attendee.name} className="rounded-full border border-border-subtle px-2.5 py-1 text-12 text-text-secondary">
                {attendee.name}
              </span>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-border-subtle bg-black/20 p-4">
          <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Recent messages</div>
          <div className="mt-3 space-y-2">
            {context.recent_messages.slice(0, 5).map((message) => (
              <div key={message.id} className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-2">
                <div className="text-13 text-text-primary">{message.sender_name}</div>
                <div className="mt-1 text-12 text-text-muted">{message.preview}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-border-subtle bg-black/20 p-4">
          <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Related ledger</div>
          <div className="mt-3 space-y-2">
            {ledger.map((entry) => (
              <div key={entry.id} className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-2">
                <div className="text-13 text-text-primary">{entry.summary}</div>
                <div className="mt-1 text-12 text-text-muted">ledger:{entry.id}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-border-subtle bg-black/20 p-4">
          <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Suggested actions</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {context.related_jiras.map((jira) => (
              <span key={jira} className="rounded-full border border-border-subtle px-2.5 py-1 text-12 text-text-secondary">{jira}</span>
            ))}
            {context.open_todos.map((todo) => (
              <span key={todo.id} className="rounded-full border border-border-subtle px-2.5 py-1 text-12 text-text-secondary">{todo.title}</span>
            ))}
          </div>
        </section>
      </div>
    </section>
  )
}
