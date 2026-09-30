import type { JiraTicket } from './mock-data'

export const JIRA_PAGE_SIZE = 15

export function summarizeJira(tickets: JiraTicket[]) {
  return {
    total: tickets.length,
    open: tickets.filter((ticket) => ticket.status === 'Open').length,
    inProgress: tickets.filter((ticket) => ticket.status === 'In Progress').length,
    blocked: tickets.filter((ticket) => ticket.status === 'Blocked').length,
  }
}

export function paginateJira(tickets: JiraTicket[], page: number, pageSize = JIRA_PAGE_SIZE) {
  const pages = Math.max(1, Math.ceil(tickets.length / pageSize))
  const current = Math.min(Math.max(1, page), pages)
  const startIndex = (current - 1) * pageSize
  const items = tickets.slice(startIndex, startIndex + pageSize)
  return {
    page: current,
    pages,
    start: tickets.length === 0 ? 0 : startIndex + 1,
    end: startIndex + items.length,
    items,
  }
}
