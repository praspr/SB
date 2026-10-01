import { useEffect, useMemo, useState } from 'react'
import { RefreshCw, Loader2, Ticket } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useJiraTickets, useSyncJira, useJiraStatus, useTrackJira, useUntrackJira } from '@/lib/queries'
import { TrackJiraForm } from '@/components/jira/TrackJiraForm'
import { JiraFilterBar, JIRA_PROJECTS, type JiraPriorityFilter, type JiraStatusFilter } from '@/components/jira/JiraFilterBar'
import { JiraTicketList } from '@/components/jira/JiraTicketList'
import { EmptyState } from '@/components/shared/EmptyState'
import { SkeletonRow } from '@/components/shared/SkeletonRow'
import { Button } from '@/components/ui/button'
import { paginateJira, summarizeJira } from '@/lib/jira-page'
import { useUiStore } from '@/lib/store'

export function JirasPage() {
  const setSettingsOpen = useUiStore((s) => s.setSettingsOpen)
  const setSettingsTab = useUiStore((s) => s.setSettingsTab)
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<JiraStatusFilter>(
    (searchParams.get('status') as JiraStatusFilter | null) ?? 'active',
  )
  const [priority, setPriority] = useState<JiraPriorityFilter>('all')
  const [projects, setProjects] = useState<string[]>([...JIRA_PROJECTS])
  const [q, setQ] = useState('')
  const [syncMsg, setSyncMsg] = useState<string | null>(null)
  const [trackValue, setTrackValue] = useState('')
  const [trackMsg, setTrackMsg] = useState<string | null>(null)
  const [trackTone, setTrackTone] = useState<'ok' | 'error' | null>(null)
  const [page, setPage] = useState(1)

  const filters = useMemo(
    () => ({
      status,
      priority,
      projects: projects.length === JIRA_PROJECTS.length ? undefined : projects,
      q,
      limit: 500,
    }),
    [status, priority, projects, q],
  )
  const { data: tickets, isLoading, isError, error } = useJiraTickets(filters)
  const { data: svcStatus, isLoading: statusLoading } = useJiraStatus()
  const syncMutation = useSyncJira()
  const trackMutation = useTrackJira()
  const untrackMutation = useUntrackJira()
  const stats = useMemo(() => summarizeJira(tickets ?? []), [tickets])
  const paged = useMemo(() => paginateJira(tickets ?? [], page), [page, tickets])

  useEffect(() => {
    setPage(1)
  }, [status, priority, projects, q])

  async function handleRefresh() {
    setSyncMsg(null)
    try {
      const r = await syncMutation.mutateAsync()
      if (r.errors.length > 0) {
        setSyncMsg(`⚠️ ${r.errors[0]}`)
      } else {
        setSyncMsg(`✓ ${r.updated_count} updated, ${r.added_count} added, ${r.unchanged_count} unchanged`)
      }
    } catch (e) {
      setSyncMsg(`✗ ${(e as Error).message}`)
    }
  }

  async function handleTrack() {
    setTrackMsg(null)
    setTrackTone(null)
    try {
      const result = await trackMutation.mutateAsync(trackValue)
      if (result.errors.length > 0 || !result.tracked) {
        setTrackTone('error')
        setTrackMsg(result.errors[0] ?? 'Could not track that JIRA')
        return
      }
      setTrackTone('ok')
      setTrackMsg(`Tracking ${result.key}`)
      setTrackValue('')
    } catch (err) {
      setTrackTone('error')
      setTrackMsg((err as Error).message)
    }
  }

  const confirmedDisconnectedEmpty = !isLoading
    && !statusLoading
    && !isError
    && (tickets?.length ?? 0) === 0
    && svcStatus?.atlassian_reachable === false

  if (isLoading && !tickets) {
    return (
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-end gap-3">
          <Button variant="secondary" disabled>
            <Loader2 size={14} className="animate-spin" />
            Refresh from Atlassian
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-20 animate-pulse rounded-xl border border-border-subtle bg-bg-panel/60" />
          ))}
        </div>
        <SkeletonRow lines={6} />
      </div>
    )
  }

  if (confirmedDisconnectedEmpty) {
    return (
      <div className="flex min-h-[68vh] items-center justify-center">
        <div className="w-full max-w-2xl rounded-[28px] border border-border-strong bg-bg-panel/92 p-6 shadow-md sm:p-8">
          <EmptyState
            title="Not connected to Atlassian"
            body="Add a JIRA token in Settings → Connections so sb can mirror your assigned issues from Atlassian into this view."
            actionLabel="Add JIRA token"
            onAction={() => {
              setSettingsTab('connections')
              setSettingsOpen(true)
            }}
            icon={<Ticket size={28} />}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-end gap-3">
        <div className="flex items-center gap-2">
          {syncMsg && <span className="text-12 text-text-secondary">{syncMsg}</span>}
          <Button variant="secondary" onClick={handleRefresh} disabled={syncMutation.isPending}>
            {syncMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Refresh from Atlassian
          </Button>
        </div>
      </div>
      {svcStatus?.atlassian_reachable === false && svcStatus.atlassian_error ? (
        <p className="text-12 text-text-muted">{svcStatus.atlassian_error}</p>
      ) : null}

      <div className="grid grid-cols-2 overflow-hidden rounded-xl border border-border-subtle bg-bg-panel/60 sm:grid-cols-4">
        {[
          { label: 'Matching', value: stats.total, tone: 'text-accent-300' },
          { label: 'Open', value: stats.open, tone: 'text-info' },
          { label: 'In progress', value: stats.inProgress, tone: 'text-warning' },
          { label: 'Blocked', value: stats.blocked, tone: 'text-danger' },
        ].map((item) => (
          <div key={item.label} className="border-b border-border-subtle px-4 py-3 last:border-0 sm:border-b-0 sm:border-r sm:last:border-r-0">
            <div className={`text-16 font-semibold tabular ${item.tone}`}>{item.value}</div>
            <div className="text-11 uppercase tracking-[0.12em] text-text-muted">{item.label}</div>
          </div>
        ))}
      </div>

      <TrackJiraForm
        value={trackValue}
        pending={trackMutation.isPending}
        message={trackMsg}
        tone={trackTone}
        onChange={setTrackValue}
        onSubmit={handleTrack}
      />

      <JiraFilterBar
        status={status}
        onStatusChange={setStatus}
        priority={priority}
        onPriorityChange={setPriority}
        projects={projects}
        onProjectsChange={setProjects}
        onSearchChange={setQ}
      />

      {isError && (
        <div className="rounded-md border border-danger/40 bg-danger/5 p-3 text-13 text-danger">
          {(error as Error)?.message ?? 'Failed to load tickets'} — is sb running on :8787?
        </div>
      )}

      <JiraTicketList
        tickets={isLoading ? undefined : paged.items}
        isLoading={isLoading}
        onUntrack={(key) => {
          void untrackMutation.mutateAsync(key).then(() => {
            setTrackTone('ok')
            setTrackMsg(`Stopped tracking ${key}; its local mirror was kept`)
          })
        }}
      />

      <div className="flex flex-wrap items-center justify-between gap-3 text-13 text-text-secondary">
        <span className="tabular">
          {paged.start}–{paged.end} of {stats.total}
          {svcStatus ? ` · ${svcStatus.tickets_count} in the local mirror` : ''}
          {svcStatus?.last_sync_at ? ` · synced ${svcStatus.last_sync_at}` : ''}
          {status === 'active' ? ' · closed hidden' : ''}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setPage((current) => current - 1)} disabled={paged.page <= 1}>
            Previous
          </Button>
          <span className="tabular">Page {paged.page} of {paged.pages}</span>
          <Button variant="secondary" onClick={() => setPage((current) => current + 1)} disabled={paged.page >= paged.pages}>
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
