import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { LandingPage } from '@/pages/LandingPage'

const mockUseJiraTickets = vi.fn()
const mockWebexAttentionFiltered = vi.fn()

vi.mock('@/lib/queries', () => ({
  useTodayTasks: () => ({ data: [], isLoading: false }),
  useTodayMeetings: () => ({ data: [], isLoading: false }),
  useTasks: () => ({ data: [] }),
  useJiraTickets: () => mockUseJiraTickets(),
  useWebexAttention: () => ({ data: [] }),
  useCompleteTask: () => ({ mutate: () => undefined }),
}))
vi.mock('@/lib/ledger', () => ({ ledgerSearch: () => Promise.resolve([]) }))
vi.mock('@/lib/signals', () => ({ searchSignals: () => Promise.resolve([]) }))
vi.mock('@/lib/triage', () => ({ webexAttentionFiltered: () => mockWebexAttentionFiltered() }))
vi.mock('@/components/landing/MorningBrief', () => ({ MorningBrief: () => <div>Morning summary</div> }))
vi.mock('@/components/landing/UsageStats', () => ({ UsageStats: () => <div>Usage metrics</div> }))
vi.mock('@/components/landing/DashboardInsights', () => ({ DashboardInsights: () => <div>Status analytics</div> }))
vi.mock('@/components/landing/ChatPanel', () => ({ ChatPanel: () => <div>Assistant panel</div> }))

describe('landing page', () => {
  it('keeps the daily sections and leaves AI usage to the navbar when attention is empty', () => {
    mockUseJiraTickets.mockReturnValue({ data: [] })
    mockWebexAttentionFiltered.mockResolvedValue([])
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <LandingPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(html).toContain('Your day at a glance')
    expect(html).toContain('priorities</h2>')
    expect(html).toContain('Upcoming meetings')
    expect(html).toContain('Plan your day')
    expect(html).not.toContain('AI usage')
    expect(html).not.toContain('Usage metrics')
    expect(html).not.toContain('Status analytics')
    expect(html).not.toContain('Ledger deltas overnight')
  })

  it('promotes attention to the top when inbox items exist', async () => {
    mockUseJiraTickets.mockReturnValue({ data: [{ key: 'CXP-30112', title: 'Blocked epic', status: 'Blocked' }] })
    mockWebexAttentionFiltered.mockResolvedValue([
      {
        id: 'm1',
        sender_name: 'Ada',
        preview: 'Can you review this?',
        triage_kind: 'mention',
      },
      {
        id: 'm2',
        sender_name: 'Bo',
        preview: 'Need your answer today',
        triage_kind: 'dm',
      },
    ])
    const client = new QueryClient()
    await client.prefetchQuery({ queryKey: ['triage', 'attention'], queryFn: () => mockWebexAttentionFiltered() })
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <LandingPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(html).toContain('Attention is stacking up')
    expect(html).toContain('Open inbox')
    expect(html).toContain('Ada')
    expect(html).toContain('Mention')
    expect(html).toContain('Bo')
    expect(html).toContain('DM')
    expect(html).toContain('+1 more waiting')
    expect(html).not.toContain('Your day at a glance')
  })
})
