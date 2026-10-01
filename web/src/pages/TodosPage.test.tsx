import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { TaskList } from '@/components/tasks/TaskList'
import { TodosPage } from '@/pages/TodosPage'

import { vi } from 'vitest'

vi.mock('@/lib/todos-rich', () => ({ fetchRichTasks: () => Promise.resolve([]) }))
vi.mock('@/lib/goals', () => ({ listGoalsV2: () => Promise.resolve([]) }))
vi.mock('@/lib/queries', () => ({
  listJiraTickets: () => Promise.resolve([{ key: 'CXP-1', status: 'Open', priority: 'High', title: 'Ticket' }]),
  useCompleteTask: () => ({ mutate: () => undefined }),
  useAddTask: () => ({ mutate: () => undefined }),
}))
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useSearchParams: () => [new URLSearchParams()] }
})

describe('todos ui', () => {
  it('renders goal, jira, and recurrence chips', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <TaskList
            tasks={[
              {
                id: 1,
                title: 'Finish rollout',
                priority: 1,
                is_completed: false,
                domain: 'work',
                source: 'jira',
                goal_id: 7,
                jira_ref: 'CXP-42',
                recurrence_rule: 'FREQ=WEEKLY',
              },
            ]}
            goalTitles={{ 7: 'Portal launch' }}
          />
        </MemoryRouter>
      </QueryClientProvider>
    )
    expect(html).toContain('Portal launch')
    expect(html).toContain('CXP-42')
    expect(html).toContain('weekly')
  })

  it('shows productivity summaries, search, sorting, and the jira action', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <TodosPage />
        </MemoryRouter>
      </QueryClientProvider>
    )
    expect(html).toContain('Overdue')
    expect(html).toContain('Due today')
    expect(html).toContain('Search todos')
    expect(html).toContain('Goal:')
    expect(html).toContain('Linked to JIRA')
    expect(html).toContain('Recurring')
    expect(html).toContain('Sort by')
    expect(html).toContain('Create todos from JIRA')
  })
})
