import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { History, Play } from 'lucide-react'
import { ledgerLog, ledgerProjects, ledgerSearch } from '@/lib/ledger'
import { reportDaily, reportMonthly, reportQuery, reportWeekly, type ReportResult } from '@/lib/reports'
import { reportStandup, reportToday, reportWrap } from '@/lib/triage'
import { ReportViewer } from '@/components/reports/ReportViewer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { LedgerEntry } from '@/lib/ledger'
import { cn } from '@/lib/utils'

type ReportTemplate = 'daily' | 'weekly' | 'monthly' | 'query' | 'today' | 'wrap' | 'standup'

type RecentRun = {
  template: ReportTemplate
  project: string
  label: string
  at: string
}

type ReportsViewProps = {
  template: ReportTemplate
  onTemplate: (value: ReportTemplate) => void
  project: string
  onProject: (value: string) => void
  date: string
  onDate: (value: string) => void
  month: string
  onMonth: (value: string) => void
  since: string
  until: string
  onSince: (value: string) => void
  onUntil: (value: string) => void
  query: string
  onQuery: (value: string) => void
  projects: Array<{ project: string }>
  report?: ReportResult | null
  citedEntries?: LedgerEntry[]
  loading?: boolean
  error?: string
  recentRuns: RecentRun[]
  savePending?: boolean
  onRun: () => void
  onCopy: () => void
  onSave: () => void
}

const RECENT_RUNS_KEY = 'sb-report-runs'

function loadRecentRuns(): RecentRun[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(RECENT_RUNS_KEY)
    return raw ? (JSON.parse(raw) as RecentRun[]) : []
  } catch {
    return []
  }
}

function saveRecentRuns(next: RecentRun[]) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(RECENT_RUNS_KEY, JSON.stringify(next.slice(0, 10)))
}

export function ReportsView({
  template,
  onTemplate,
  project,
  onProject,
  date,
  onDate,
  month,
  onMonth,
  since,
  until,
  onSince,
  onUntil,
  query,
  onQuery,
  projects,
  report,
  citedEntries,
  loading,
  error,
  recentRuns,
  savePending,
  onRun,
  onCopy,
  onSave,
}: ReportsViewProps) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Reports</h1>
          <p className="mt-1 text-13 text-text-secondary">Run ledger-backed daily, weekly, monthly, and ad-hoc summaries.</p>
        </div>
      </div>

      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {(['today', 'wrap', 'standup', 'daily', 'weekly', 'monthly', 'query'] as ReportTemplate[]).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => onTemplate(value)}
                  className={cn(
                    'rounded-lg border px-3 py-2 text-13 capitalize transition-colors duration-fast ease-out',
                    template === value
                      ? 'border-border-strong bg-accent-500/15 text-text-primary'
                      : 'border-border-subtle bg-black/20 text-text-secondary hover:border-border-strong hover:text-text-primary'
                  )}
                >
                  {value}
                </button>
              ))}
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
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

              {template === 'daily' && (
                <label className="space-y-1.5">
                  <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Date</span>
                  <Input type="date" value={date} onChange={(event) => onDate(event.target.value)} />
                </label>
              )}

              {template === 'weekly' && (
                <label className="space-y-1.5">
                  <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Week end</span>
                  <Input type="date" value={date} onChange={(event) => onDate(event.target.value)} />
                </label>
              )}

              {template === 'monthly' && (
                <label className="space-y-1.5">
                  <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Month</span>
                  <Input type="month" value={month} onChange={(event) => onMonth(event.target.value)} />
                </label>
              )}

              {template === 'query' && (
                <>
                  <label className="space-y-1.5">
                    <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Since</span>
                    <Input type="date" value={since} onChange={(event) => onSince(event.target.value)} />
                  </label>
                  <label className="space-y-1.5">
                    <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Until</span>
                    <Input type="date" value={until} onChange={(event) => onUntil(event.target.value)} />
                  </label>
                  <label className="space-y-1.5 md:col-span-2">
                    <span className="text-12 uppercase tracking-[0.18em] text-text-muted">Query</span>
                    <Input value={query} onChange={(event) => onQuery(event.target.value)} placeholder="What changed around release notes?" />
                  </label>
                </>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Button variant="primary" onClick={onRun}>
                <Play size={14} />
                Run
              </Button>
              <div className="text-12 text-text-muted">Citations stay local and open the referenced ledger entries on the right.</div>
            </div>
          </div>

          <aside className="rounded-lg border border-border-subtle bg-black/20 p-4">
            <div className="flex items-center gap-2 text-14 font-semibold text-text-primary">
              <History size={14} />
              Recent runs
            </div>
            {recentRuns.length === 0 ? (
              <p className="mt-3 text-13 text-text-muted">Recent report runs appear here after your first execution.</p>
            ) : (
              <div className="mt-3 space-y-2">
                {recentRuns.map((run, index) => (
                  <div key={`${run.at}-${index}`} className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-2">
                    <div className="text-13 text-text-primary">{run.label}</div>
                    <div className="mt-1 text-12 text-text-muted">{run.template} · {run.project || 'all projects'} · {run.at}</div>
                  </div>
                ))}
              </div>
            )}
          </aside>
        </div>
      </section>

      <ReportViewer
        report={report}
        entries={citedEntries}
        loading={loading}
        error={error}
        canSave={Boolean(project && report?.markdown)}
        savePending={savePending}
        template={template}
        date={date}
        onCopy={onCopy}
        onSave={onSave}
      />
    </div>
  )
}

export function ReportsPage() {
  const today = new Date().toISOString().slice(0, 10)
  const [template, setTemplate] = useState<ReportTemplate>('daily')
  const [project, setProject] = useState('')
  const [date, setDate] = useState(today)
  const [month, setMonth] = useState(today.slice(0, 7))
  const [since, setSince] = useState(today)
  const [until, setUntil] = useState(today)
  const [query, setQuery] = useState('')
  const [report, setReport] = useState<ReportResult | null>(null)
  const [error, setError] = useState<string>()
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>(() => loadRecentRuns())

  const projects = useQuery({ queryKey: ['ledger', 'projects'], queryFn: ledgerProjects, staleTime: 30_000 })

  const citedEntries = useQuery({
    queryKey: ['reports', 'citations', report?.citations],
    queryFn: async () => {
      const ids = report?.citations ?? []
      if (!ids.length) return []
      const rows = await ledgerSearch({ limit: 500 })
      return rows.filter((row) => ids.includes(row.id))
    },
    enabled: Boolean(report?.citations?.length),
    staleTime: 30_000,
  })

  const runReport = useMutation({
    mutationFn: async () => {
      if (template === 'daily') return reportDaily(date, project || undefined)
      if (template === 'weekly') return reportWeekly(date, project || undefined)
      if (template === 'monthly') return reportMonthly(month, project || undefined)
      if (template === 'today') return reportToday(date)
      if (template === 'wrap') return reportWrap()
      if (template === 'standup') return reportStandup(date)
      return reportQuery({
        q: query,
        project: project || undefined,
        since: since ? `${since}T00:00:00Z` : undefined,
        until: until ? `${until}T23:59:59Z` : undefined,
      })
    },
    onSuccess: (data) => {
      if (data.error) {
        setError(data.error)
        setReport(null)
        return
      }
      setError(undefined)
      setReport(data)
      const label = template === 'query'
        ? query || 'ad-hoc query'
        : template === 'monthly'
          ? month
          : template === 'wrap'
            ? 'wrap'
            : date
      const next = [{ template, project, label, at: new Date().toLocaleString() }, ...recentRuns].slice(0, 10)
      setRecentRuns(next)
      saveRecentRuns(next)
    },
    onError: (err: Error) => {
      setError(err.message || 'Could not run report.')
      setReport(null)
    },
  })

  const saveNote = useMutation({
    mutationFn: async () => {
      if (!report?.markdown || !project) return null
      return ledgerLog({
        project,
        action_verb: 'Noted',
        summary: `Saved ${template} report snapshot`,
        body: report.markdown,
        source_harness: 'web',
      })
    },
  })

  const viewerError = error || (projects.isError ? 'Could not load enrolled projects.' : undefined)
  const allProjects = useMemo(() => projects.data ?? [], [projects.data])

  return (
    <ReportsView
      template={template}
      onTemplate={setTemplate}
      project={project}
      onProject={setProject}
      date={date}
      onDate={setDate}
      month={month}
      onMonth={setMonth}
      since={since}
      until={until}
      onSince={setSince}
      onUntil={setUntil}
      query={query}
      onQuery={setQuery}
      projects={allProjects}
      report={report}
      citedEntries={citedEntries.data}
      loading={runReport.isPending || citedEntries.isFetching}
      error={viewerError}
      recentRuns={recentRuns}
      savePending={saveNote.isPending}
      onRun={() => runReport.mutate()}
      onCopy={() => {
        if (report?.markdown && navigator.clipboard) void navigator.clipboard.writeText(report.markdown)
      }}
      onSave={() => saveNote.mutate()}
    />
  )
}
