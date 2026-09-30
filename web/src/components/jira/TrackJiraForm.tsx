import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function TrackJiraForm({
  value,
  pending,
  message,
  tone,
  onChange,
  onSubmit,
}: {
  value: string
  pending: boolean
  message: string | null
  tone: 'ok' | 'error' | null
  onChange: (value: string) => void
  onSubmit: () => void
}) {
  return (
    <form
      className="flex flex-wrap items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
    >
      <input
        aria-label="JIRA link or key"
        value={value}
        disabled={pending}
        onChange={(event) => onChange(event.target.value)}
        placeholder="CXP-123 or Atlassian browse link"
        className="min-w-0 flex-1 rounded-md border border-border-subtle bg-black/20 px-2 py-1.5 text-13 text-text-primary"
      />
      <Button type="submit" variant="secondary" disabled={pending || value.trim().length === 0}>
        {pending ? <Loader2 size={14} className="animate-spin" /> : null}
        Track JIRA
      </Button>
      {message ? (
        <span className={tone === 'error' ? 'text-12 text-danger' : 'text-12 text-text-secondary'}>{message}</span>
      ) : null}
    </form>
  )
}
