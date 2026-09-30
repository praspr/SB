import { useState, type ReactNode } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Loader2, RefreshCw, X } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ledgerProjects, ledgerRegisterProject, ledgerSessions } from '@/lib/ledger'
import { SETTING_CHECKS, type CheckResult } from '@/lib/settings-checks'
import { fetchCoreStatus } from '@/lib/status'
import { cn } from '@/lib/utils'

type SettingsPopoverProps = {
  children: ReactNode
}

export function SettingsPopover({ children }: SettingsPopoverProps) {
  const queryClient = useQueryClient()
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null)
  const [tab, setTab] = useState('connections')
  const [projectName, setProjectName] = useState('')
  const [rootPath, setRootPath] = useState('')
  const [changelogPath, setChangelogPath] = useState('')

  const checks = useQueries({
    queries: SETTING_CHECKS.map((check) => ({
      queryKey: ['setting-check', check.id],
      queryFn: check.fn,
      staleTime: 15_000,
      retry: 0,
    })),
  })

  const coreStatusQuery = useQuery({
    queryKey: ['core-status'],
    queryFn: async () => {
      const data = await fetchCoreStatus()
      setRefreshedAt(new Date())
      return data
    },
    staleTime: 15_000,
    retry: 0,
  })
  const projectsQuery = useQuery({ queryKey: ['ledger', 'projects'], queryFn: ledgerProjects, staleTime: 15_000, retry: 0 })
  const sessionsQuery = useQuery({ queryKey: ['ledger', 'sessions'], queryFn: () => ledgerSessions(20), staleTime: 15_000, retry: 0 })
  const enroll = useMutation({
    mutationFn: ledgerRegisterProject,
    onSuccess: () => {
      setProjectName('')
      setRootPath('')
      setChangelogPath('')
      void queryClient.invalidateQueries({ queryKey: ['ledger', 'projects'] })
    },
  })

  const rows = SETTING_CHECKS.map((check, index) => {
    const query = checks[index]
    const data = query.data

    if (query.isPending || !data) {
      return {
        name: check.id,
        label: check.label,
        status: 'loading',
        subtext: undefined,
      } satisfies CheckResult
    }

    return data
  })

  const isRefreshing = checks.some((query) => query.isFetching) || coreStatusQuery.isFetching

  return (
    <Popover>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent
        side="right"
        align="end"
        collisionPadding={12}
        className="w-[340px] rounded-xl border-border-strong bg-bg-panel p-4"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-14 font-semibold text-text-primary">Settings</h2>
            <button
              type="button"
              aria-label="Refresh settings checks"
              onClick={() => {
                void queryClient.invalidateQueries({ queryKey: ['setting-check'] })
                void queryClient.invalidateQueries({ queryKey: ['core-status'] })
              }}
              className="inline-flex items-center justify-center rounded-md border border-border-subtle p-1.5 text-text-muted transition-colors duration-fast ease-out hover:border-border-strong hover:text-text-primary"
            >
              <RefreshCw size={14} className={cn(isRefreshing && 'animate-spin')} />
            </button>
          </div>

          <Tabs value={tab} onValueChange={setTab}>
            <TabsList className="grid grid-cols-4 gap-1">
              <TabsTrigger value="connections">Connections</TabsTrigger>
              <TabsTrigger value="diagnostics">Diagnostics</TabsTrigger>
              <TabsTrigger value="projects">Projects</TabsTrigger>
              <TabsTrigger value="sessions">Sessions</TabsTrigger>
            </TabsList>

            <TabsContent value="connections" className="space-y-2.5">
              <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Connections</div>
              <div className="space-y-1.5">
                {rows.map((row) => (
                  <div
                    key={row.name}
                    className="flex items-start gap-3 rounded-lg border border-border-subtle bg-black/20 px-3 py-2.5"
                  >
                    <div className="flex h-[18px] w-[18px] shrink-0 items-center justify-center pt-0.5">
                      {row.status === 'loading' && <Loader2 size={16} className="animate-spin text-text-muted" />}
                      {row.status === 'ok' && <Check size={16} className="text-success" />}
                      {row.status === 'fail' && <X size={16} className="text-danger" />}
                      {row.status === 'unknown' && <span className="h-2 w-2 rounded-full bg-text-muted" />}
                    </div>
                    <div className="min-w-0">
                      <div className="text-13 text-text-primary">{row.label}</div>
                      {row.subtext && <div className="mt-0.5 text-12 text-text-muted">{row.subtext}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="diagnostics" className="space-y-2.5">
              <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Diagnostics</div>
              <dl className="grid gap-3 sm:grid-cols-2">
                <div>
                  <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Database</dt>
                  <dd className="mt-1 text-14 text-text-primary">
                    {coreStatusQuery.data ? (coreStatusQuery.data.database.ready ? 'ready' : 'not ready') : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Schema version</dt>
                  <dd className="mt-1 text-14 text-text-primary">
                    {coreStatusQuery.data?.database.schema_version ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Service version</dt>
                  <dd className="mt-1 text-14 text-text-primary">{coreStatusQuery.data?.version ?? '—'}</dd>
                </div>
                <div>
                  <dt className="text-12 uppercase tracking-[0.18em] text-text-muted">Last refresh</dt>
                  <dd className="mt-1 text-14 text-text-primary">{refreshedAt ? refreshedAt.toLocaleString() : 'not yet'}</dd>
                </div>
              </dl>
              <div className="flex flex-wrap gap-2 text-13 text-text-secondary">
                <span className="rounded-full border border-border-subtle px-2.5 py-1">
                  tools {coreStatusQuery.data?.counts.tools ?? '—'}
                </span>
                <span className="rounded-full border border-border-subtle px-2.5 py-1">
                  prompts {coreStatusQuery.data?.counts.prompts ?? '—'}
                </span>
                <span className="rounded-full border border-border-subtle px-2.5 py-1">
                  resources {coreStatusQuery.data?.counts.resources ?? '—'}
                </span>
              </div>
            </TabsContent>

            <TabsContent value="projects" className="space-y-3">
              <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Projects</div>
              <div className="space-y-2">
                {(projectsQuery.data ?? []).map((project) => (
                  <div key={project.project} className="rounded-lg border border-border-subtle bg-black/20 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-13 font-medium text-text-primary">{project.project}</div>
                        <div className="mt-1 truncate text-12 text-text-muted">{project.root_path}</div>
                        <div className="mt-1 truncate text-12 text-text-muted">{project.changelog_path}</div>
                      </div>
                      <Button
                        variant="secondary"
                        className="px-2.5 py-1 text-12"
                        onClick={() => enroll.mutate({
                          project: project.project,
                          root_path: project.root_path,
                          changelog_path: project.changelog_path,
                          sync_mode: project.sync_mode === 'dual' ? 'sqlite-only' : 'dual',
                        })}
                      >
                        {project.sync_mode === 'dual' ? 'Dual' : 'SQLite only'}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="rounded-lg border border-border-subtle bg-black/20 p-3">
                <div className="text-13 font-medium text-text-primary">Enroll a project</div>
                <div className="mt-3 space-y-2">
                  <Input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Project key" />
                  <Input value={rootPath} onChange={(event) => setRootPath(event.target.value)} placeholder="Root path" />
                  <Input value={changelogPath} onChange={(event) => setChangelogPath(event.target.value)} placeholder="Optional changelog path" />
                  <Button
                    variant="secondary"
                    disabled={!projectName || !rootPath || enroll.isPending}
                    onClick={() => enroll.mutate({
                      project: projectName,
                      root_path: rootPath,
                      changelog_path: changelogPath || undefined,
                      sync_mode: 'dual',
                    })}
                  >
                    Enroll
                  </Button>
                </div>
                <div className="mt-2 text-12 text-text-muted">Registry enrollment is immediate. Auto-scan lands in a later phase.</div>
              </div>
            </TabsContent>

            <TabsContent value="sessions" className="space-y-3">
              <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Sessions</div>
              <div className="space-y-2">
                {(sessionsQuery.data ?? []).map((session) => (
                  <div key={session.session_id} className="rounded-lg border border-border-subtle bg-black/20 p-3">
                    <div className="text-13 font-medium text-text-primary">{session.project || 'unknown project'}</div>
                    <div className="mt-1 text-12 text-text-muted">{session.session_id}</div>
                    <div className="mt-1 text-12 text-text-muted">{session.started_at} · {session.entry_count} entries</div>
                  </div>
                ))}
              </div>
            </TabsContent>
          </Tabs>

          <div className="text-12 text-text-muted">Local sb MCP readiness. No credentials are shown.</div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
