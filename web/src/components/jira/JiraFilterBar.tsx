import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import type { JiraPriority, JiraStatus } from '@/lib/mock-data'

export type JiraStatusFilter = JiraStatus | 'all'
export type JiraPriorityFilter = JiraPriority | 'all'
export type JiraProjectFilter = string | 'all'

const statusOptions: { value: JiraStatusFilter; label: string }[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'Open', label: 'Open' },
  { value: 'In Progress', label: 'In Progress' },
  { value: 'In Engineering Review', label: 'In Engineering Review' },
  { value: 'Code Review', label: 'Code Review' },
  { value: 'Dev Complete', label: 'Dev Complete' },
  { value: 'In Testing', label: 'In Testing' },
  { value: 'Blocked', label: 'Blocked' },
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

const projectOptions: { value: JiraProjectFilter; label: string }[] = [
  { value: 'all', label: 'All projects' },
  { value: 'CXP', label: 'CXP' },
  { value: 'CXPL', label: 'CXPL' },
]

const selectClasses =
  'h-9 rounded-md border border-border-subtle bg-bg-panel px-2.5 text-13 text-text-primary outline-none transition-colors duration-fast ease-out focus:border-accent-500 focus:ring-1 focus:ring-accent-500'

export function JiraFilterBar({
  status,
  onStatusChange,
  priority,
  onPriorityChange,
  project,
  onProjectChange,
  onSearchChange,
}: {
  status: JiraStatusFilter
  onStatusChange: (v: JiraStatusFilter) => void
  priority: JiraPriorityFilter
  onPriorityChange: (v: JiraPriorityFilter) => void
  project: JiraProjectFilter
  onProjectChange: (v: JiraProjectFilter) => void
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

      <select
        value={project}
        onChange={(e) => onProjectChange(e.target.value as JiraProjectFilter)}
        className={selectClasses}
      >
        {projectOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}
