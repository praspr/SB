import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { StorageGauge } from '@/components/landing/StorageGauge'
import type { CoreStatus } from '@/lib/status'

const mockFetchCoreStatus = vi.fn()
vi.mock('@/lib/status', () => ({ fetchCoreStatus: () => mockFetchCoreStatus() }))

function baseStatus(percent: number): CoreStatus {
  const total = 1_000_000_000_000
  const used = Math.round((percent / 100) * total)
  return {
    status: 'ok',
    version: '0',
    database: { ready: true, schema_version: 11 },
    disk: { total, used, free: total - used, percent },
    counts: { tools: 1, prompts: 0, resources: 0 },
  }
}

async function renderGauge(status: CoreStatus | null, error = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  if (error) {
    mockFetchCoreStatus.mockRejectedValue(new Error('down'))
    // Drive the query to a settled error state before rendering.
    try {
      await client.fetchQuery({ queryKey: ['system', 'status', 'disk'], queryFn: () => mockFetchCoreStatus() })
    } catch {
      // expected — query is now cached as errored
    }
  } else {
    mockFetchCoreStatus.mockResolvedValue(status)
    await client.prefetchQuery({ queryKey: ['system', 'status', 'disk'], queryFn: () => mockFetchCoreStatus() })
  }
  return renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <StorageGauge />
    </QueryClientProvider>,
  )
}

describe('StorageGauge', () => {
  it('shows used/total/free and a healthy tone under 70%', async () => {
    const html = await renderGauge(baseStatus(42))
    expect(html).toContain('Storage')
    expect(html).toContain('free')
    expect(html).toContain('42')
    expect(html).toContain('text-success-fg')
  })

  it('uses a warning tone between 70 and 90%', async () => {
    const html = await renderGauge(baseStatus(80))
    expect(html).toContain('text-warning-fg')
  })

  it('uses a danger tone at or above 90%', async () => {
    const html = await renderGauge(baseStatus(95))
    expect(html).toContain('text-danger-fg')
  })

  it('degrades to unavailable when disk data is missing', async () => {
    const html = await renderGauge({ ...baseStatus(10), disk: null })
    expect(html).toContain('Unavailable')
  })

  it('renders the storage card without a ring while a fetch is unresolved/errored', async () => {
    const html = await renderGauge(null, true)
    // On error/loading in SSR, no disk ring renders; the HardDrive fallback shows.
    expect(html).toContain('Storage')
    expect(html).toContain('lucide-hard-drive')
    expect(html).not.toContain('used')
  })
})
