import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { HealthStrip } from '@/components/landing/HealthStrip'

vi.mock('@/components/landing/SystemClock', () => ({ SystemClock: () => <div>clock</div> }))
vi.mock('@/components/landing/StorageGauge', () => ({ StorageGauge: () => <div>storage</div> }))
vi.mock('@/components/landing/UsageRing', () => ({
  ClaudegateUsageRing: () => <div>claudegate</div>,
  CursorUsageRing: () => <div>cursor</div>,
}))

function render(jirasPending: number) {
  const client = new QueryClient()
  const now = new Date('2026-10-25T12:00:00Z')
  return renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <HealthStrip jirasPending={jirasPending} now={now} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('HealthStrip', () => {
  it('lays out clock, storage, usage rings, and pending JIRAs', () => {
    const html = render(5)
    expect(html).toContain('clock')
    expect(html).toContain('storage')
    expect(html).toContain('claudegate')
    expect(html).toContain('cursor')
    expect(html).toContain('JIRAs pending')
    expect(html).toContain('5')
    expect(html).toContain('open + active')
    expect(html).toContain('href="/jira"')
  })

  it('shows all clear when no JIRAs are pending', () => {
    const html = render(0)
    expect(html).toContain('all clear')
  })
})
