import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { LandingPage } from '@/pages/LandingPage'

vi.mock('@/lib/queries', () => ({
  useTodayTasks: () => ({ data: [], isLoading: false }),
  useTodayMeetings: () => ({ data: [], isLoading: false }),
  useTasks: () => ({ data: [] }),
  useJiraTickets: () => ({ data: [] }),
  useWebexAttention: () => ({ data: [] }),
  useCompleteTask: () => ({ mutate: () => undefined }),
}))
vi.mock('@/lib/ledger', () => ({ ledgerSearch: () => Promise.resolve([]) }))
vi.mock('@/lib/signals', () => ({ searchSignals: () => Promise.resolve([]) }))
vi.mock('@/lib/triage', () => ({ webexAttentionFiltered: () => Promise.resolve([]) }))
vi.mock('@/components/landing/MorningBrief', () => ({ MorningBrief: () => <div>Morning summary</div> }))
vi.mock('@/components/landing/UsageStats', () => ({ UsageStats: () => <div>Usage metrics</div> }))
vi.mock('@/components/landing/DashboardInsights', () => ({ DashboardInsights: () => <div>Status analytics</div> }))
vi.mock('@/components/landing/ChatPanel', () => ({ ChatPanel: () => <div>Assistant panel</div> }))

describe('landing page', () => {
  it('keeps the daily sections and leaves AI usage to the navbar', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <LandingPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(html).toContain('Needs attention')
    expect(html).toContain('priorities</h2>')
    expect(html).toContain('Upcoming meetings')
    expect(html).not.toContain('AI usage')
    expect(html).not.toContain('Usage metrics')
    expect(html).not.toContain('Status analytics')
    expect(html).not.toContain('Ledger deltas overnight')
  })
})
