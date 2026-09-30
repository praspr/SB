import type { JiraPriority, JiraStatus } from './mock-data'

export type StatusCategory = 'open' | 'active' | 'done' | 'cancelled'

export function statusCategory(status: JiraStatus): StatusCategory {
  switch (status) {
    case 'Open':
      return 'open'
    case 'In Progress':
    case 'In Engineering Review':
    case 'Code Review':
    case 'Dev Complete':
    case 'In Testing':
    case 'Blocked':
    case 'Pending Approval':
      return 'active'
    case 'Test Complete':
    case 'Done':
    case 'Resolved':
    case 'Closed':
      return 'done'
    case 'Cancelled':
      return 'cancelled'
    default:
      return 'open'
  }
}

export function statusColorClasses(status: JiraStatus): string {
  switch (statusCategory(status)) {
    case 'open':
      return 'bg-neutral-800 text-text-secondary border border-border-subtle'
    case 'active':
      return 'bg-warning/15 text-warning border border-warning/30'
    case 'done':
      return 'bg-success/15 text-success border border-success/30'
    case 'cancelled':
      return 'bg-danger/10 text-danger/80 border border-danger/20'
    default:
      return 'bg-neutral-800 text-text-secondary border border-border-subtle'
  }
}

export function priorityColor(priority: JiraPriority): string {
  switch (priority) {
    case 'Highest':
      return 'bg-danger/15 text-danger border border-danger/30'
    case 'High':
      return 'bg-warning/15 text-warning border border-warning/30'
    case 'Medium':
      return 'bg-info/15 text-info border border-info/30'
    case 'Low':
      return 'bg-neutral-800 text-text-secondary border border-border-subtle'
    case 'Lowest':
      return 'bg-neutral-800 text-text-muted border border-border-subtle'
    default:
      return 'bg-neutral-800 text-text-secondary border border-border-subtle'
  }
}
