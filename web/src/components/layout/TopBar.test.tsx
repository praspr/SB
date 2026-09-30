import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { TopBar } from '@/components/layout/TopBar'

vi.mock('@/components/landing/UsageStats', () => ({
  UsageStats: () => <div>Usage metrics</div>,
}))

describe('top bar', () => {
  it('shows the system clock and AI usage beside the page actions', () => {
    const html = renderToStaticMarkup(
      <TopBar now={new Date(2026, 9, 1, 0, 24)} />,
    )

    expect(html).toContain('justify-self-center')
    expect(html).toContain('Thursday, October 1 · 12:24 AM')
    expect(html).toContain('Usage metrics')
    expect(html).not.toContain('sb dashboard')
    expect(html).not.toContain('Add todo')
    expect(html).not.toContain('Command palette')
  })
})
