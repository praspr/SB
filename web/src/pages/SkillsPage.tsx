import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { getSkill, listSkills, syncSkills, type SkillDetail, type SkillSummary, type SkillSyncResult } from '@/lib/skills'
import { cn } from '@/lib/utils'

export type SkillFilters = {
  source: string
  status: string
  query: string
}

export function SkillsView({
  skills,
  filters,
  onFilters,
  detail,
  onOpen,
  onClose,
  syncing,
  syncResult,
  error,
  onSync,
}: {
  skills: SkillSummary[] | undefined
  filters: SkillFilters
  onFilters: (next: SkillFilters) => void
  detail?: SkillDetail | null
  onOpen: (id: string) => void
  onClose: () => void
  syncing: boolean
  syncResult?: SkillSyncResult | null
  error?: string
  onSync: () => void
}) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-20 font-semibold text-text-primary">Skills</h1>
          <p className="mt-1 text-13 text-text-secondary">
            Procedures discovered from allow-listed skill directories.
          </p>
        </div>
        <button
          type="button"
          onClick={onSync}
          disabled={syncing}
          className="inline-flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-panel px-3 py-1.5 text-13 text-text-secondary"
        >
          <RefreshCw size={14} className={syncing ? 'animate-spin' : undefined} />
          {syncing ? 'Syncing skills' : 'Sync skills'}
        </button>
      </div>

      {error && (
        <p className="rounded-md border border-danger/40 bg-danger/5 p-3 text-13 text-danger">{error}</p>
      )}
      {syncResult && (
        <p className="text-13 text-text-secondary">
          Sync result: {syncResult.added} added, {syncResult.updated} updated, {syncResult.unavailable} unavailable
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <input
          aria-label="Search skills"
          value={filters.query}
          onChange={(event) => onFilters({ ...filters, query: event.target.value })}
          placeholder="Search"
          className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-1.5 text-13"
        />
        <select
          aria-label="Skill source"
          value={filters.source}
          onChange={(event) => onFilters({ ...filters, source: event.target.value })}
          className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-1.5 text-13"
        >
          {['all', 'project', 'cursor', 'claude', 'configured'].map((source) => (
            <option key={source} value={source}>
              {source}
            </option>
          ))}
        </select>
        <select
          aria-label="Skill status"
          value={filters.status}
          onChange={(event) => onFilters({ ...filters, status: event.target.value })}
          className="rounded-lg border border-border-subtle bg-bg-panel px-3 py-1.5 text-13"
        >
          {['all', 'available', 'unavailable'].map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </div>

      <ul className="space-y-2">
        {(skills ?? []).map((skill) => (
          <li key={skill.id}>
            <button
              type="button"
              onClick={() => onOpen(skill.id)}
              className="w-full rounded-xl border border-border-subtle bg-bg-panel/92 p-4 text-left"
            >
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-14 font-semibold text-text-primary">{skill.name}</h2>
                <span className={cn('text-12', skill.available ? 'text-success' : 'text-danger')}>
                  {skill.available ? 'available' : 'unavailable'}
                </span>
              </div>
              <p className="mt-1 text-13 text-text-secondary">{skill.description}</p>
              <p className="mt-2 text-12 text-text-muted">
                {skill.source}
                {skill.modified_at ? ` · ${skill.modified_at}` : ''}
                {skill.allowed_tools.length ? ` · ${skill.allowed_tools.join(', ')}` : ''}
              </p>
            </button>
          </li>
        ))}
      </ul>

      {detail && (
        <aside className="rounded-xl border border-border-strong bg-bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-16 font-semibold text-text-primary">{detail.name}</h2>
            <button type="button" onClick={onClose} className="text-13 text-text-muted">
              Close
            </button>
          </div>
          <pre className="mt-3 whitespace-pre-wrap text-13 text-text-secondary">{detail.procedure}</pre>
        </aside>
      )}
    </div>
  )
}

export function SkillsPage() {
  const client = useQueryClient()
  const [filters, setFilters] = useState<SkillFilters>({ source: 'all', status: 'all', query: '' })
  const [detail, setDetail] = useState<SkillDetail | null>(null)
  const [syncError, setSyncError] = useState<string>()
  const skills = useQuery({
    queryKey: ['skills', filters],
    queryFn: () => listSkills(filters),
  })
  const sync = useMutation({
    mutationFn: syncSkills,
    onSuccess: () => {
      setSyncError(undefined)
      void client.invalidateQueries({ queryKey: ['skills'] })
    },
    onError: (error: Error) => setSyncError(error.message),
  })

  return (
    <SkillsView
      skills={skills.data}
      filters={filters}
      onFilters={setFilters}
      detail={detail}
      onOpen={(id) => {
        void getSkill(id).then((found) => setDetail(found))
      }}
      onClose={() => setDetail(null)}
      syncing={sync.isPending}
      syncResult={sync.data}
      error={skills.isError ? 'Could not load skills.' : syncError}
      onSync={() => sync.mutate()}
    />
  )
}
