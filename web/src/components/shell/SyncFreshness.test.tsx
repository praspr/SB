import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { SyncFreshness, minutesSinceLatestSuccess, syncFreshnessTone } from '@/components/shell/SyncFreshness'

vi.mock('@/lib/sync-status', () => ({
  syncStatus: () => Promise.resolve({
    states: [
      { adapter: 'jira', last_run_at: '2026-10-01T10:00:00.000Z', signal_count: 4, error: null },
    ],
  }),
}))

describe('SyncFreshness', () => {
  it('computes freshness thresholds', () => {
    expect(minutesSinceLatestSuccess([{ last_run_at: '2026-10-01T10:00:00.000Z', error: null }], new Date('2026-10-01T10:10:00.000Z'))).toBe(10)
    expect(syncFreshnessTone(10)).toBe('green')
    expect(syncFreshnessTone(30)).toBe('amber')
    expect(syncFreshnessTone(60)).toBe('red')
  })

  it('renders the freshness pill label', async () => {
    const client = new QueryClient()
    await client.prefetchQuery({
      queryKey: ['sync-status', 'freshness'],
      queryFn: async () => ({
        states: [{ adapter: 'jira', last_run_at: '2026-10-01T10:00:00.000Z', signal_count: 4, error: null }],
      }),
    })

    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <SyncFreshness now={new Date('2026-10-01T10:10:00.000Z')} />
      </QueryClientProvider>,
    )

    expect(html).toContain('10m since sync')
  })
})
