import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { DashboardInsights, summarizeDashboard } from './DashboardInsights'
import type { JiraTicket, Task } from '@/lib/mock-data'
import type { SignalRecord } from '@/lib/signals'

const tasks = [
  { id: 1, title: 'Open', priority: 1, is_completed: false, domain: 'work', source: 'manual' },
  { id: 2, title: 'Done', priority: 2, is_completed: true, domain: 'work', source: 'manual' },
] as Task[]

const tickets = [
  { key: 'CXP-1', status: 'Open', priority: 'High', project: 'CXP' },
  { key: 'CXP-2', status: 'Open', priority: 'Medium', project: 'CXP' },
  { key: 'CXPL-3', status: 'Blocked', priority: 'Highest', project: 'CXPL' },
] as JiraTicket[]

const signals = [
  { id: 1, source: 'jira', kind: 'ticket', occurred_at: '2026-09-30', title: 'One' },
  { id: 2, source: 'git', kind: 'commit', occurred_at: '2026-09-30', title: 'Two' },
  { id: 3, source: 'git', kind: 'commit', occurred_at: '2026-09-29', title: 'Three' },
] as SignalRecord[]

describe('dashboard insights', () => {
  it('summarizes todos, JIRA, and signals without fixed status assumptions', () => {
    const summary = summarizeDashboard(tasks, tickets, signals)
    expect(summary.todos).toEqual([
      { label: 'Open', value: 1 },
      { label: 'Completed', value: 1 },
    ])
    expect(summary.jira).toContainEqual({ label: 'Open', value: 2 })
    expect(summary.jira).toContainEqual({ label: 'Blocked', value: 1 })
    expect(summary.signals).toContainEqual({ label: 'git', value: 2 })
  })

  it('renders operational charts with drill-down links', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <DashboardInsights tasks={tasks} tickets={tickets} signals={signals} />
      </MemoryRouter>,
    )
    expect(html).toContain('Work pulse')
    expect(html).toContain('JIRA status')
    expect(html).toContain('/jira?status=Blocked')
    expect(html).toContain('/todos')
    expect(html).toContain('/signals?source=git')
  })
})

