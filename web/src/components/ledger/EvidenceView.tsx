import { RefreshCw } from 'lucide-react'
import { cite, type AdapterState, type SignalRecord } from '@/lib/signals'

export function EvidenceView({
  signals,
  states,
  query,
  onQuery,
  syncing,
  error,
  onSync,
}: {
  signals: SignalRecord[] | undefined
  states: AdapterState[] | undefined
  query: string
  onQuery: (value: string) => void
  syncing: boolean
  error?: string
  onSync: () => void
}) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Evidence</div>
          <p className="mt-1 text-13 text-text-secondary">Local signals you can cite as evidence alongside ledger rows.</p>
        </div>
        <button type="button" onClick={onSync} className="inline-flex items-center gap-2 rounded-lg border border-border-subtle px-3 py-1.5 text-13">
          <RefreshCw size={14} className={syncing ? 'animate-spin' : undefined} />
          {syncing ? 'Syncing adapters' : 'Sync adapters'}
        </button>
      </div>

      {error ? <p className="text-13 text-danger">{error}</p> : null}

      <input
        aria-label="Search evidence"
        value={query}
        onChange={(event) => onQuery(event.target.value)}
        placeholder="Search local evidence"
        className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-1.5 text-13"
      />

      <ul className="space-y-2">
        {(states ?? []).map((state) => (
          <li key={state.adapter} className="text-12 text-text-muted">
            {state.adapter}: {state.signal_count} signals{state.error ? ` · ${state.error}` : ''}
          </li>
        ))}
      </ul>

      <ul className="space-y-2">
        {(signals ?? []).map((signal) => (
          <li key={signal.id} className="rounded-xl border border-border-subtle bg-bg-panel/92 p-4">
            <div className="text-14 text-text-primary">{cite(signal)}</div>
            <div className="mt-1 text-12 text-text-muted">
              {signal.source} · {signal.kind} · {signal.occurred_at}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
