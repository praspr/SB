import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { cite, searchSignals, syncAdapters, syncStatus, type AdapterState, type SignalRecord } from '@/lib/signals'

export function SignalsView({
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
          <h1 className="text-20 font-semibold text-text-primary">Signals</h1>
          <p className="mt-1 text-13 text-text-secondary">Local evidence cited as [signal:N].</p>
        </div>
        <button type="button" onClick={onSync} className="inline-flex items-center gap-2 rounded-lg border border-border-subtle px-3 py-1.5 text-13">
          <RefreshCw size={14} className={syncing ? 'animate-spin' : undefined} />
          {syncing ? 'Syncing adapters' : 'Sync adapters'}
        </button>
      </div>
      {error && <p className="text-13 text-danger">{error}</p>}
      <input
        aria-label="Search signals"
        value={query}
        onChange={(event) => onQuery(event.target.value)}
        placeholder="Search signals"
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

export function SignalsPage() {
  const client = useQueryClient()
  const [searchParams] = useSearchParams()
  const source = searchParams.get('source') ?? undefined
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string>()
  const signals = useQuery({
    queryKey: ['signals', query, source],
    queryFn: () => searchSignals({ query, source }),
  })
  const status = useQuery({ queryKey: ['sync-status'], queryFn: syncStatus })
  const sync = useMutation({
    mutationFn: syncAdapters,
    onSuccess: () => {
      setError(undefined)
      void client.invalidateQueries({ queryKey: ['signals'] })
      void client.invalidateQueries({ queryKey: ['sync-status'] })
    },
    onError: (err: Error) => setError(err.message),
  })
  return (
    <SignalsView
      signals={signals.data}
      states={status.data?.states}
      query={query}
      onQuery={setQuery}
      syncing={sync.isPending}
      error={signals.isError ? 'Could not load signals.' : error}
      onSync={() => sync.mutate()}
    />
  )
}
