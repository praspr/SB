import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { LandingPage } from '@/pages/LandingPage'

const mockUseJiraTickets = vi.fn()
const mockWebexAttentionFiltered = vi.fn()
const mockUseWebexStatus = vi.fn()
const mockUseJiraStatus = vi.fn()
const mockLedgerSearch = vi.fn()
const mockLedgerProjects = vi.fn()
const mockListGoalsV2 = vi.fn()

vi.mock('@/lib/queries', () => ({
  useTodayTasks: () => ({ data: [], isLoading: false }),
  useTodayMeetings: () => ({ data: [], isLoading: false }),
  useTasks: () => ({ data: [] }),
  useJiraTickets: () => mockUseJiraTickets(),
  useWebexStatus: () => mockUseWebexStatus(),
  useJiraStatus: () => mockUseJiraStatus(),
  useWebexAttention: () => ({ data: [] }),
  useCompleteTask: () => ({ mutate: () => undefined }),
}))
vi.mock('@/lib/ledger', () => ({ ledgerSearch: () => mockLedgerSearch(), ledgerProjects: () => mockLedgerProjects() }))
vi.mock('@/lib/goals', () => ({ listGoalsV2: () => mockListGoalsV2() }))
vi.mock('@/lib/signals', () => ({ searchSignals: () => Promise.resolve([]) }))
vi.mock('@/lib/triage', () => ({ webexAttentionFiltered: () => mockWebexAttentionFiltered() }))
vi.mock('@/lib/store', () => ({
  useUiStore: (selector: (state: any) => unknown) => selector({
    setSettingsOpen: () => undefined,
    setSettingsTab: () => undefined,
  }),
}))
vi.mock('@/components/landing/UsageStats', () => ({ UsageStats: () => <div>Usage metrics</div> }))
vi.mock('@/components/landing/DashboardInsights', () => ({ DashboardInsights: () => <div>Status analytics</div> }))
vi.mock('@/components/landing/HealthStrip', () => ({ HealthStrip: ({ jirasPending }: { jirasPending: number }) => <div>Health strip ({jirasPending} jiras pending)</div> }))
vi.mock('@/components/landing/ChatPanel', () => ({ ChatPanel: () => <div>Assistant panel</div> }))

describe('landing page', () => {
  it('keeps the daily sections and inlines work analytics while leaving AI usage to the navbar when attention is empty', () => {
    mockUseJiraTickets.mockReturnValue({ data: [] })
    mockWebexAttentionFiltered.mockResolvedValue([])
    mockUseWebexStatus.mockReturnValue({ data: { authenticated: false } })
    mockUseJiraStatus.mockReturnValue({ data: { atlassian_reachable: false } })
    mockLedgerSearch.mockResolvedValue([])
    mockLedgerProjects.mockResolvedValue([])
    mockListGoalsV2.mockResolvedValue([])
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <LandingPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(html).toContain('Your day at a glance')
    expect(html).toContain('Health strip')
    expect(html).toContain('priorities today')
    expect(html).toContain('Upcoming meetings')
    expect(html).toContain('New todo')
    expect(html).toContain('Overdue')
    expect(html).toContain('Get started')
    expect(html).toContain('View today&#x27;s brief →')
    expect(html).toContain('Status analytics')
    expect(html).not.toContain('AI usage')
    expect(html).not.toContain('Usage metrics')
    expect(html).not.toContain('Attention is stacking up')
  })

  it('no longer shows the attention banner on the landing page even when inbox items exist', async () => {
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
    mockUseWebexStatus.mockReturnValue({ data: { authenticated: true } })
    mockUseJiraStatus.mockReturnValue({ data: { atlassian_reachable: true } })
    mockLedgerSearch.mockResolvedValue([{ id: 1 }])
    mockLedgerProjects.mockResolvedValue([{ project: 'sb' }])
    mockListGoalsV2.mockResolvedValue([{ id: 1, title: 'Launch', tier: 'weekly', keywords: [], status: 'active' }])
    const client = new QueryClient()
    await client.prefetchQuery({ queryKey: ['triage', 'attention'], queryFn: () => mockWebexAttentionFiltered() })
    await client.prefetchQuery({ queryKey: ['landing', 'ledger-preview'], queryFn: () => mockLedgerSearch() })
    await client.prefetchQuery({ queryKey: ['landing', 'projects'], queryFn: () => mockLedgerProjects() })
    await client.prefetchQuery({ queryKey: ['landing', 'goals'], queryFn: () => mockListGoalsV2() })
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <LandingPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    // Attention banner is removed from the landing page entirely.
    expect(html).not.toContain('Attention is stacking up')
    expect(html).not.toContain('Open inbox')
    expect(html).not.toContain('more waiting')
    // The day-at-a-glance hero always shows instead.
    expect(html).toContain('Your day at a glance')
    expect(html).toContain('need attention')
  })
})
