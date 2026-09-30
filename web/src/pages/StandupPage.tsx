import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getStandup, standupText, type Standup } from '@/lib/standup'

export function StandupView({
  standup,
  error,
  copied,
  onCopy,
}: {
  standup?: Standup | null
  error?: string
  copied: boolean
  onCopy: () => void
}) {
  const bullets = standup?.bullets ?? []
  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Standup</h1>
          <p className="mt-1 text-13 text-text-secondary">
            Five to eight bullets from the plan, yesterday&apos;s wrap, and open work.
          </p>
        </div>
        <button
          type="button"
          onClick={onCopy}
          disabled={bullets.length === 0}
          className="rounded-lg border border-border-subtle px-3 py-1.5 text-13"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      {error && <p className="text-13 text-danger">{error}</p>}
      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        {bullets.length === 0 ? (
          <p className="text-13 text-text-muted">No standup yet.</p>
        ) : (
          <ul className="space-y-2 text-13 text-text-secondary">
            {bullets.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

export function StandupPage() {
  const [copied, setCopied] = useState(false)
  const standup = useQuery({ queryKey: ['standup'], queryFn: () => getStandup() })
  const bullets = standup.data?.bullets ?? []
  return (
    <StandupView
      standup={standup.data}
      error={standup.isError ? 'Could not load standup.' : undefined}
      copied={copied}
      onCopy={() => {
        if (bullets.length === 0 || typeof navigator === 'undefined' || !navigator.clipboard) {
          return
        }
        void navigator.clipboard.writeText(standupText(bullets)).then(() => {
          setCopied(true)
        })
      }}
    />
  )
}
