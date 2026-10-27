import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { ClaudegateUsageRing, CursorUsageRing } from '@/components/landing/UsageRing'

const mockClaudegate = vi.fn()
const mockCursor = vi.fn()
vi.mock('@/lib/queries', () => ({
  useClaudegateUsage: () => mockClaudegate(),
  useCursorUsage: () => mockCursor(),
}))

describe('UsageRing', () => {
  it('renders claudegate usage with remaining, plan and reset', () => {
    mockClaudegate.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        plan: 'Pro',
        premium: { used: 250, total: 1000, remaining: 750 },
        reset_date: '2026-11-01',
      },
    })
    const html = renderToStaticMarkup(<ClaudegateUsageRing />)
    expect(html).toContain('Claudegate')
    expect(html).toContain('250')
    expect(html).toContain('1,000')
    expect(html).toContain('750 left')
    expect(html).toContain('Pro')
  })

  it('shows claudegate unavailable on error', () => {
    mockClaudegate.mockReturnValue({ isLoading: false, isError: true, data: null })
    const html = renderToStaticMarkup(<ClaudegateUsageRing />)
    expect(html).toContain('Unavailable')
  })

  it('shows cursor not-signed-in state', () => {
    mockCursor.mockReturnValue({
      isLoading: false,
      isError: true,
      error: new Error('cursor: not signed in'),
      data: null,
    })
    const html = renderToStaticMarkup(<CursorUsageRing />)
    expect(html).toContain('Cursor')
    expect(html).toContain('Not signed in')
  })

  it('renders cursor usage when data present', () => {
    mockCursor.mockReturnValue({
      isLoading: false,
      isError: false,
      data: { primaryUsed: 40, primaryTotal: 500, membershipType: 'business', resetDate: null },
    })
    const html = renderToStaticMarkup(<CursorUsageRing />)
    expect(html).toContain('40')
    expect(html).toContain('500')
    expect(html).toContain('460 left')
    expect(html).toContain('business')
  })
})
