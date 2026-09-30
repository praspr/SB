import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { TaskList } from '@/components/tasks/TaskList'

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
})
