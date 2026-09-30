import { describe, expect, it } from 'vitest'
import type { JiraTicket } from './mock-data'
import { paginateJira, summarizeJira } from './jira-page'

const ticket = (overrides: Partial<JiraTicket>): JiraTicket => ({
  key: 'CXP-1',
  project: 'CXP',
  title: 'Ticket',
  status: 'Open',
  priority: 'Medium',
  issue_type: 'Bug',
  assignee: { name: 'Ada', email: 'ada@example.com' },
  created: '2026-09-01T00:00:00Z',
  updated: '2026-09-30T00:00:00Z',
  labels: [],
  fix_versions: [],
  description: '',
  url: 'https://example.test/CXP-1',
  ...overrides,
})

describe('jira page summary', () => {
  it('counts the visible statuses', () => {
    expect(summarizeJira([
      ticket({ key: 'CXP-1', status: 'Open' }),
      ticket({ key: 'CXP-2', status: 'In Progress' }),
      ticket({ key: 'CXP-3', status: 'Blocked' }),
      ticket({ key: 'CXP-4', status: 'Open' }),
    ])).toEqual({ total: 4, open: 2, inProgress: 1, blocked: 1 })
  })

  it('returns one page of tickets and the matching range', () => {
    const tickets = Array.from({ length: 16 }, (_, index) => ticket({ key: `CXP-${index + 1}` }))
    expect(paginateJira(tickets, 2)).toMatchObject({
      page: 2,
      pages: 2,
      start: 16,
      end: 16,
      items: [expect.objectContaining({ key: 'CXP-16' })],
    })
  })
})
