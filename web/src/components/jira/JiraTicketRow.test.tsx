import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { JiraTicketRow } from './JiraTicketRow'
import type { JiraTicket } from '@/lib/mock-data'

function ticket(tracked: boolean): JiraTicket {
  return {
    key: 'CXP-77',
    project: 'CXP',
    title: 'Review parser',
    status: 'Open',
    priority: 'High',
    issue_type: 'Task',
    assignee: { name: 'Ada', email: 'ada@example.com' },
    created: '2026-09-01T00:00:00Z',
    updated: '2026-09-30T00:00:00Z',
    labels: [],
    fix_versions: [],
    description: 'Review parser changes',
    url: 'https://cisco-cxe.atlassian.net/browse/CXP-77',
    tracked,
  }
}

describe('jira ticket row actions', () => {
  it('always offers todo creation and only untracks tracked tickets', () => {
    const tracked = renderToStaticMarkup(<JiraTicketRow ticket={ticket(true)} onUntrack={() => undefined} />)
    expect(tracked).toContain('Create todo')
    expect(tracked).toContain('Untrack')

    const assigned = renderToStaticMarkup(<JiraTicketRow ticket={ticket(false)} onUntrack={() => undefined} />)
    expect(assigned).toContain('Create todo')
    expect(assigned).not.toContain('Untrack')
  })
})
