import { formatDistanceToNow } from 'date-fns'
import type { JiraTicket } from '@/lib/mock-data'
import { priorityColor, statusColorClasses } from '@/lib/jira-utils'
import { cn } from '@/lib/utils'
import { useUiStore } from '@/lib/store'
import { Button } from '@/components/ui/button'

function initials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function JiraTicketRow({
  ticket,
  onUntrack,
}: {
  ticket: JiraTicket
  onUntrack?: (key: string) => void
}) {
  const openAddTodo = useUiStore((state) => state.openAddTodo)
  function handleClick() {
    window.open(ticket.url, '_blank', 'noopener,noreferrer')
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleClick()
        }
      }}
      className="group flex min-h-[40px] cursor-pointer items-center gap-3 rounded-lg border border-border-subtle bg-bg-panel px-3 py-2 transition-colors duration-fast ease-out hover:border-border-strong hover:bg-bg-elevated"
    >
      <span className="w-[92px] shrink-0 text-13 tabular font-medium text-text-secondary">{ticket.key}</span>

      <div className="min-w-0 flex-1">
        <div className="truncate text-14 font-medium text-text-primary">{ticket.title}</div>
        <div className="mt-0.5 flex items-center gap-2 text-12 text-text-muted">
          <span>{ticket.issue_type}</span>
          {ticket.labels.length > 0 && (
            <>
              <span>·</span>
              <span className="truncate">{ticket.labels.join(', ')}</span>
            </>
          )}
        </div>
      </div>

      <span className={cn('shrink-0 rounded px-2 py-0.5 text-xs font-medium', statusColorClasses(ticket.status))}>
        {ticket.status}
      </span>

      <span className={cn('shrink-0 rounded px-2 py-0.5 text-xs font-medium', priorityColor(ticket.priority))}>
        {ticket.priority}
      </span>

      <span
        title={ticket.assignee.name}
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border-subtle bg-black/20 text-12 font-semibold text-text-secondary"
      >
        {initials(ticket.assignee.name)}
      </span>

      <span className="w-20 shrink-0 text-right text-12 tabular text-text-muted">
        {formatDistanceToNow(new Date(ticket.updated), { addSuffix: true })}
      </span>
      <Button
        variant="ghost"
        onClick={(event) => {
          event.stopPropagation()
          openAddTodo({
            title: `Review ${ticket.key}: ${ticket.title}`,
            description: `${ticket.description || ticket.title}\n\n[JIRA:${ticket.key}]`,
            priority: ticket.priority === 'Highest' ? 1 : ticket.priority === 'High' ? 2 : 3,
            external_source: 'jira',
            external_ref: ticket.key,
            jira_ref: ticket.key,
          })
        }}
      >
        Create todo
      </Button>
      {ticket.tracked && onUntrack ? (
        <Button
          variant="ghost"
          onClick={(event) => {
            event.stopPropagation()
            onUntrack(ticket.key)
          }}
        >
          Untrack
        </Button>
      ) : null}
    </div>
  )
}
