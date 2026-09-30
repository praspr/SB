import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import type { JiraPriority, JiraStatus } from '@/lib/mock-data'

export type JiraStatusFilter = JiraStatus | 'all' | 'active'
export type JiraPriorityFilter = JiraPriority | 'all'
export const JIRA_PROJECTS = ['CXP', 'CXPL', 'FSRE'] as const

const statusOptions: { value: JiraStatusFilter; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'all', label: 'All statuses' },
  { value: 'Open', label: 'Open' },
  { value: 'In Progress', label: 'In Progress' },
  { value: 'In Engineering Review', label: 'In Engineering Review' },
  { value: 'Code Review', label: 'Code Review' },
  { value: 'Dev Complete', label: 'Dev Complete' },
  { value: 'In Testing', label: 'In Testing' },
  { value: 'Test Complete', label: 'Test Complete' },
  { value: 'Pending Approval', label: 'Pending Approval' },
  { value: 'Blocked', label: 'Blocked' },
  { value: 'Done', label: 'Done' },
  { value: 'Resolved', label: 'Resolved' },
  { value: 'Closed', label: 'Closed' },
  { value: 'Cancelled', label: 'Cancelled' },
]

const priorityOptions: { value: JiraPriorityFilter; label: string }[] = [
  { value: 'all', label: 'All priorities' },
  { value: 'Highest', label: 'Highest' },
  { value: 'High', label: 'High' },
  { value: 'Medium', label: 'Medium' },
  { value: 'Low', label: 'Low' },
  { value: 'Lowest', label: 'Lowest' },
]

const selectClasses =
  'h-9 rounded-md border border-border-subtle bg-bg-panel px-2.5 text-13 text-text-primary outline-none transition-colors duration-fast ease-out focus:border-accent-500 focus:ring-1 focus:ring-accent-500'

export function JiraFilterBar({
  status,
  onStatusChange,
  priority,
  onPriorityChange,
  projects,
  onProjectsChange,
  onSearchChange,
}: {
  status: JiraStatusFilter
  onStatusChange: (v: JiraStatusFilter) => void
  priority: JiraPriorityFilter
  onPriorityChange: (v: JiraPriorityFilter) => void
  projects: string[]
  onProjectsChange: (v: string[]) => void
  onSearchChange: (v: string) => void
}) {
  const [q, setQ] = useState('')

  useEffect(() => {
    const t = setTimeout(() => onSearchChange(q), 200)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q])

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative w-full max-w-xs">
        <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search title or key…"
          className={cn('pl-8')}
        />
      </div>

      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value as JiraStatusFilter)}
        className={selectClasses}
      >
        {statusOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        value={priority}
        onChange={(e) => onPriorityChange(e.target.value as JiraPriorityFilter)}
        className={selectClasses}
      >
        {priorityOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <fieldset className="flex h-9 items-center gap-3 rounded-md border border-border-subtle bg-bg-panel px-2.5">
        <legend className="sr-only">Projects</legend>
        {JIRA_PROJECTS.map((name) => (
          <label key={name} className="flex items-center gap-1.5 text-13 text-text-primary">
            <input
              type="checkbox"
              checked={projects.includes(name)}
              onChange={() => {
                const next = projects.includes(name)
                  ? projects.filter((item) => item !== name)
                  : [...projects, name]
                onProjectsChange(next)
              }}
            />
            {name}
          </label>
        ))}
      </fieldset>
    </div>
  )
}
