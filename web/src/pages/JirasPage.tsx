import { useMemo, useState } from 'react'
import { RefreshCw, Loader2 } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useJiraTickets, useSyncJira, useJiraStatus, useTrackJira, useUntrackJira } from '@/lib/queries'
import { TrackJiraForm } from '@/components/jira/TrackJiraForm'
import { JiraFilterBar, JIRA_PROJECTS, type JiraPriorityFilter, type JiraStatusFilter } from '@/components/jira/JiraFilterBar'
import { JiraTicketList } from '@/components/jira/JiraTicketList'
import { Button } from '@/components/ui/button'

export function JirasPage() {
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
  const { data: svcStatus } = useJiraStatus()
  const syncMutation = useSyncJira()
  const trackMutation = useTrackJira()
  const untrackMutation = useUntrackJira()

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

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">JIRAs</h1>
          <p className="mt-1 text-13 text-text-secondary">
            Local mirror at ciq/docs/jira/tickets
            {svcStatus ? ` · ${svcStatus.tickets_count} tickets` : ''}
            {svcStatus?.last_sync_at ? ` · last sync ${svcStatus.last_sync_at}` : ''}
          </p>
          {svcStatus?.atlassian_reachable === false && svcStatus.atlassian_error ? (
            <p className="mt-1 text-12 text-text-muted">{svcStatus.atlassian_error}</p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {syncMsg && <span className="text-12 text-text-secondary">{syncMsg}</span>}
          <Button variant="secondary" onClick={handleRefresh} disabled={syncMutation.isPending}>
            {syncMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Refresh from Atlassian
          </Button>
        </div>
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
        tickets={tickets}
        isLoading={isLoading}
        onUntrack={(key) => {
          void untrackMutation.mutateAsync(key).then(() => {
            setTrackTone('ok')
            setTrackMsg(`Stopped tracking ${key}; its local mirror was kept`)
          })
        }}
      />

      <p className="text-12 text-text-muted">
        Same tickets as ciq/docs/jira/README.md
        {status === 'active' ? ' · closed tickets hidden' : ''} · showing {tickets?.length ?? 0}
        {svcStatus?.tickets_count != null ? ` of ${svcStatus.tickets_count}` : ''} · pull-only Atlassian sync
      </p>
    </div>
  )
}
