import { Video, MapPin, Users, Crown } from 'lucide-react'
import type { Meeting } from '@/lib/mock-data'
import { formatTime, initials } from '@/lib/utils'

export function MeetingCard({ meeting }: { meeting: Meeting }) {
  return (
    <div className="rounded-lg border border-border-subtle bg-bg-panel p-4 transition-colors duration-fast ease-out hover:border-border-strong hover:bg-bg-elevated">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-14 font-semibold text-text-primary">{meeting.title}</h3>
            {meeting.is_organizer && (
              <span title="You're organizing">
                <Crown size={12} className="shrink-0 text-warning" />
              </span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-2 text-12 tabular text-text-secondary">
            <span>
              {formatTime(meeting.start)} – {formatTime(meeting.end)}
            </span>
            {meeting.location && (
              <>
                <span>·</span>
                <span className="flex items-center gap-1">
                  <MapPin size={11} /> {meeting.location}
                </span>
              </>
            )}
          </div>
        </div>
        {meeting.join_url && (
          <a
            href={meeting.join_url}
            target="_blank"
            rel="noreferrer"
            className="flex shrink-0 items-center gap-1.5 rounded-md border border-border-strong bg-accent-500 px-2.5 py-1.5 text-12 font-medium text-white transition hover:brightness-110"
          >
            <Video size={12} /> Join
          </a>
        )}
      </div>

      {meeting.agenda && <p className="mt-2 text-13 leading-5 text-text-secondary">{meeting.agenda}</p>}

      <div className="mt-3 flex items-center gap-2">
        <div className="flex -space-x-2">
          {meeting.attendees.slice(0, 4).map((a) => (
            <div
              key={a.email || a.name}
              title={a.name}
              className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-bg-panel bg-accent-800 text-[10px] font-semibold text-text-primary"
            >
              {initials(a.name)}
            </div>
          ))}
        </div>
        <span className="flex items-center gap-1 text-12 text-text-muted">
          <Users size={11} /> {meeting.attendees.length}
        </span>
      </div>
    </div>
  )
}
