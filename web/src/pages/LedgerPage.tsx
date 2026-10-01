import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Search } from 'lucide-react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/shared/EmptyState'
import { SkeletonRow } from '@/components/shared/SkeletonRow'
import { LedgerTable } from '@/components/ledger/LedgerTable'
import { LedgerTimeline } from '@/components/ledger/LedgerTimeline'
import { EvidenceView } from '@/components/ledger/EvidenceView'
import { ledgerProjects, ledgerSearch, type LedgerEntry } from '@/lib/ledger'
import { searchSignals, syncAdapters, syncStatus, type AdapterState, type SignalRecord } from '@/lib/signals'
import { cn } from '@/lib/utils'
import { useSearchParams } from 'react-router-dom'

type LedgerViewMode = 'timeline' | 'table' | 'evidence'

type LedgerPageViewProps = {
  projects: Array<{ project: string }>
  project: string
  onProject: (value: string) => void
  sourceHarness: string
  onSourceHarness: (value: string) => void
  sessionId: string
  onSessionId: (value: string) => void
  sessions: string[]
  search: string
  onSearch: (value: string) => void
  since: string
  onSince: (value: string) => void
  until: string
  onUntil: (value: string) => void
  verbs: string[]
  selectedVerbs: string[]
  onToggleVerb: (verb: string) => void
  view: LedgerViewMode
  onView: (mode: LedgerViewMode) => void
  harnesses: string[]
  entries: LedgerEntry[]
  evidenceSignals: SignalRecord[]
  evidenceStates: AdapterState[]
  evidenceQuery: string
  onEvidenceQuery: (value: string) => void
  onEvidenceSync: () => void
  evidenceSyncing?: boolean
  evidenceError?: string
  loading?: boolean
  error?: string
  selectedEntry: LedgerEntry | null
  onSelectEntry: (entry: LedgerEntry | null) => void
  onLoadOlder: () => void
}

function toSinceValue(value: string | null): string {
  if (value === '24h') return new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
  return value ?? ''
}

function unique<T>(values: T[]): T[] {
  return Array.from(new Set(values))
}

export function LedgerPageView({
  projects,
  project,
  onProject,
  sourceHarness,
  onSourceHarness,
  sessionId,
  onSessionId,
  sessions,
  search,
  onSearch,
  since,
  onSince,
  until,
  onUntil,
  verbs,
  selectedVerbs,
  onToggleVerb,
  view,
  onView,
  harnesses,
  entries,
  evidenceSignals,
  evidenceStates,
  evidenceQuery,
  onEvidenceQuery,
  onEvidenceSync,
  evidenceSyncing,
  evidenceError,
  loading,
  error,
  selectedEntry,
  onSelectEntry,
  onLoadOlder,
}: LedgerPageViewProps) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Ledger</h1>
          <p className="mt-1 text-13 text-text-secondary">Search the append-only narrative ledger by project, session, and source.</p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-panel p-1">
          {(['timeline', 'table', 'evidence'] as LedgerViewMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => onView(mode)}
              className={cn(
                'rounded-md px-3 py-1.5 text-13 capitalize text-text-secondary transition-colors duration-fast ease-out',
                view === mode && 'bg-accent-500/15 text-text-primary'
              )}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <div className="grid gap-3 xl:grid-cols-[repeat(4,minmax(0,1fr))_1.3fr]">
          <label className="space-y-1.5">
            <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Project</span>
            <select
              value={project}
              onChange={(event) => onProject(event.target.value)}
              className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-3 text-13 text-text-primary outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500"
            >
              <option value="">All projects</option>
              {projects.map((item) => (
                <option key={item.project} value={item.project}>{item.project}</option>
              ))}
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Since</span>
            <Input type="datetime-local" value={since ? since.slice(0, 16) : ''} onChange={(event) => onSince(event.target.value ? new Date(event.target.value).toISOString() : '')} />
          </label>

          <label className="space-y-1.5">
            <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Until</span>
            <Input type="datetime-local" value={until ? until.slice(0, 16) : ''} onChange={(event) => onUntil(event.target.value ? new Date(event.target.value).toISOString() : '')} />
          </label>

          <label className="space-y-1.5">
            <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Source harness</span>
            <select
              value={sourceHarness}
              onChange={(event) => onSourceHarness(event.target.value)}
              className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-3 text-13 text-text-primary outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500"
            >
              <option value="">All sources</option>
              {harnesses.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>

          <label className="space-y-1.5 xl:col-span-1">
            <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Search</span>
            <div className="relative">
              <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <Input className="pl-9" value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search the ledger" />
            </div>
          </label>
        </div>

        <div className="mt-3 grid gap-3 xl:grid-cols-[1.2fr_1fr]">
          <label className="space-y-1.5">
            <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Session</span>
            <>
              <Input list="ledger-sessions" value={sessionId} onChange={(event) => onSessionId(event.target.value)} placeholder="Filter by session id" />
              <datalist id="ledger-sessions">
                {sessions.map((item) => <option key={item} value={item} />)}
              </datalist>
            </>
          </label>

          <div className="space-y-1.5">
            <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Verbs</span>
            <div className="flex flex-wrap gap-2">
              {verbs.length === 0 ? <span className="text-12 text-text-muted">Run a search to load available verbs.</span> : verbs.map((verb) => {
                const active = selectedVerbs.includes(verb)
                return (
                  <button
                    key={verb}
                    type="button"
                    onClick={() => onToggleVerb(verb)}
                    className={cn(
                      'rounded-full border px-2.5 py-1 text-12 transition-colors duration-fast ease-out',
                      active
                        ? 'border-border-strong bg-accent-500/15 text-text-primary'
                        : 'border-border-subtle bg-black/20 text-text-secondary hover:border-border-strong hover:text-text-primary'
                    )}
                  >
                    {verb}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      {view === 'evidence' ? (
        <EvidenceView
          signals={evidenceSignals}
          states={evidenceStates}
          query={evidenceQuery}
          onQuery={onEvidenceQuery}
          syncing={Boolean(evidenceSyncing)}
          error={evidenceError}
          onSync={onEvidenceSync}
        />
      ) : loading ? (
        <SkeletonRow lines={5} />
      ) : error ? (
        <div className="rounded-md border border-danger/40 bg-danger/5 p-3 text-13 text-danger">{error}</div>
      ) : entries.length === 0 ? (
        <EmptyState title="No ledger rows match" body="Try widening the time range or removing one filter." icon={<BookOpen size={18} />} />
      ) : view === 'table' ? (
        <LedgerTable entries={entries} onSelect={onSelectEntry} />
      ) : (
        <LedgerTimeline entries={entries} onSelect={onSelectEntry} />
      )}

      <div className="sticky bottom-4 flex justify-center">
        <Button variant="secondary" onClick={onLoadOlder}>
          Load older
        </Button>
      </div>

      <Dialog open={Boolean(selectedEntry)} onOpenChange={(open) => !open && onSelectEntry(null)}>
        <DialogContent className="left-auto right-0 top-0 h-screen w-full max-w-[420px] translate-x-0 translate-y-0 rounded-none border-l border-border-strong p-5">
          {selectedEntry && (
            <div className="space-y-4">
              <DialogTitle>{selectedEntry.summary}</DialogTitle>
              <div className="space-y-1 text-12 text-text-muted">
                <div>{selectedEntry.ts}</div>
                <div>{selectedEntry.project} · {selectedEntry.action_verb} · {selectedEntry.source_harness}</div>
                <div>session {selectedEntry.session_id || '—'}</div>
              </div>
              <div className="rounded-lg border border-border-subtle bg-black/20 p-4 text-13 leading-6 text-text-secondary">
                {selectedEntry.body || selectedEntry.summary}
              </div>
              <div>
                <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Refs</div>
                <div className="mt-2 space-y-2">
                  {selectedEntry.refs.length === 0 ? (
                    <div className="text-13 text-text-muted">No refs recorded.</div>
                  ) : selectedEntry.refs.map((ref, index) => (
                    <a
                      key={`${ref.kind}-${ref.value}-${index}`}
                      href={ref.url || '#'}
                      target={ref.url ? '_blank' : undefined}
                      rel={ref.url ? 'noreferrer' : undefined}
                      className={cn(
                        'block rounded-lg border border-border-subtle px-3 py-2 text-13 text-text-secondary',
                        ref.url && 'hover:border-border-strong hover:text-text-primary'
                      )}
                    >
                      <div className="text-text-primary">{ref.label || ref.value}</div>
                      <div className="mt-1 text-12 text-text-muted">{ref.kind}</div>
                    </a>
                  ))}
                </div>
              </div>
              <div className="text-12 text-text-muted">Redaction applied: {selectedEntry.redaction_applied ? 'yes' : 'no'}</div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export function LedgerPage() {
  const client = useQueryClient()
  const [params] = useSearchParams()
  const [project, setProject] = useState(params.get('project') ?? '')
  const [sourceHarness, setSourceHarness] = useState(params.get('source_harness') ?? '')
  const [sessionId, setSessionId] = useState(params.get('session') ?? '')
  const [search, setSearch] = useState(params.get('q') ?? '')
  const [debouncedSearch, setDebouncedSearch] = useState(params.get('q') ?? '')
  const [since, setSince] = useState(toSinceValue(params.get('since')))
  const [until, setUntil] = useState(params.get('until') ?? '')
  const [limit, setLimit] = useState(100)
  const [view, setView] = useState<LedgerViewMode>((params.get('view') as LedgerViewMode | null) ?? 'timeline')
  const [selectedVerbs, setSelectedVerbs] = useState<string[]>([])
  const [selectedEntry, setSelectedEntry] = useState<LedgerEntry | null>(null)
  const [evidenceQuery, setEvidenceQuery] = useState('')
  const [evidenceError, setEvidenceError] = useState<string>()

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 200)
    return () => window.clearTimeout(timer)
  }, [search])

  const projects = useQuery({ queryKey: ['ledger', 'projects'], queryFn: ledgerProjects, staleTime: 30_000 })

  const searchQuery = useQuery({
    queryKey: ['ledger', 'search', project, since, until, sessionId, debouncedSearch, limit, selectedVerbs],
    queryFn: async () => {
      const serverVerb = selectedVerbs.length === 1 ? selectedVerbs[0] : undefined
      return ledgerSearch({
        project: project || undefined,
        since: since || undefined,
        until: until || undefined,
        session_id: sessionId || undefined,
        q: debouncedSearch || undefined,
        verb: serverVerb,
        limit,
      })
    },
  })
  const evidenceSignals = useQuery({
    queryKey: ['signals', 'ledger-evidence', evidenceQuery],
    queryFn: () => searchSignals({ query: evidenceQuery || undefined }),
    enabled: view === 'evidence',
  })
  const evidenceStates = useQuery({
    queryKey: ['sync-status', 'ledger-evidence'],
    queryFn: syncStatus,
    enabled: view === 'evidence',
  })
  const syncEvidence = useMutation({
    mutationFn: syncAdapters,
    onSuccess: () => {
      setEvidenceError(undefined)
      void client.invalidateQueries({ queryKey: ['signals'] })
      void client.invalidateQueries({ queryKey: ['sync-status'] })
      void evidenceSignals.refetch()
      void evidenceStates.refetch()
    },
    onError: (err: Error) => setEvidenceError(err.message),
  })

  const allRows = searchQuery.data ?? []

  const verbs = useMemo(() => unique(allRows.map((row) => row.action_verb)).slice(0, 12), [allRows])
  const sessions = useMemo(() => unique(allRows.map((row) => row.session_id).filter(Boolean)).slice(0, 40), [allRows])
  const harnesses = useMemo(() => unique(allRows.map((row) => row.source_harness)).slice(0, 12), [allRows])

  const filtered = useMemo(() => {
    return allRows.filter((row) => {
      if (sourceHarness && row.source_harness !== sourceHarness) return false
      if (selectedVerbs.length > 1 && !selectedVerbs.includes(row.action_verb)) return false
      return true
    })
  }, [allRows, selectedVerbs, sourceHarness])

  useEffect(() => {
    const entryId = Number(params.get('entry'))
    if (!entryId) return
    const found = filtered.find((row) => row.id === entryId)
    if (found) setSelectedEntry(found)
  }, [filtered, params])

  return (
    <LedgerPageView
      projects={projects.data ?? []}
      project={project}
      onProject={setProject}
      sourceHarness={sourceHarness}
      onSourceHarness={setSourceHarness}
      sessionId={sessionId}
      onSessionId={setSessionId}
      sessions={sessions}
      search={search}
      onSearch={setSearch}
      since={since}
      onSince={setSince}
      until={until}
      onUntil={setUntil}
      verbs={verbs}
      selectedVerbs={selectedVerbs}
      onToggleVerb={(verb) => setSelectedVerbs((current) => current.includes(verb) ? current.filter((item) => item !== verb) : [...current, verb])}
      view={view}
      onView={setView}
      harnesses={harnesses}
      entries={filtered}
      evidenceSignals={evidenceSignals.data ?? []}
      evidenceStates={evidenceStates.data?.states ?? []}
      evidenceQuery={evidenceQuery}
      onEvidenceQuery={setEvidenceQuery}
      onEvidenceSync={() => {
        syncEvidence.mutate()
      }}
      evidenceSyncing={syncEvidence.isPending}
      evidenceError={evidenceSignals.isError ? 'Could not load evidence.' : evidenceError}
      loading={searchQuery.isLoading}
      error={searchQuery.isError ? 'Could not load ledger entries.' : undefined}
      selectedEntry={selectedEntry}
      onSelectEntry={setSelectedEntry}
      onLoadOlder={() => setLimit((value) => value + 100)}
    />
  )
}
