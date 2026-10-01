import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { JirasPage } from '@/pages/JirasPage'

vi.mock('@/lib/queries', () => ({
  useJiraTickets: () => ({ data: [], isLoading: false, isError: false, error: null }),
  useJiraStatus: () => ({
    data: { atlassian_reachable: false, atlassian_error: 'missing token', tickets_count: 0, last_sync_at: null },
    isLoading: false,
  }),
  useSyncJira: () => ({ mutateAsync: () => Promise.resolve({ errors: [], updated_count: 0, added_count: 0, unchanged_count: 0 }), isPending: false }),
  useTrackJira: () => ({ mutateAsync: () => Promise.resolve({ tracked: true, errors: [], key: 'CXP-1' }), isPending: false }),
  useUntrackJira: () => ({ mutateAsync: () => Promise.resolve({ tracked: false, errors: [], key: 'CXP-1' }), isPending: false }),
}))

vi.mock('@/lib/store', () => ({
  useUiStore: (selector: (state: any) => unknown) => selector({
    setSettingsOpen: () => undefined,
    setSettingsTab: () => undefined,
  }),
}))

describe('jira page', () => {
  it('shows the full-page Atlassian empty state once disconnection is confirmed', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <JirasPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(html).toContain('Not connected to Atlassian')
    expect(html).toContain('Add a JIRA token in Settings')
    expect(html).toContain('Add JIRA token')
    expect(html).not.toContain('Page 1 of')
  })
})
