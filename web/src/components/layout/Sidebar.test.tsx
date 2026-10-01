import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/triage', () => ({ webexAttentionRanked: () => Promise.resolve([]) }))
vi.mock('@/components/layout/SettingsPopover', () => ({
  SettingsPopover: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import { Sidebar } from '@/components/layout/Sidebar'

describe('Sidebar', () => {
  it('renders grouped navigation sections in the new order', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      </QueryClientProvider>
    )
    expect(html).toContain('DO NOW')
    expect(html).toContain('THINK')
    expect(html).toContain('SYSTEM')
    expect(html.indexOf('Attention')).toBeLessThan(html.indexOf('Todos'))
    expect(html.indexOf('Todos')).toBeLessThan(html.indexOf('Meetings'))
    expect(html.indexOf('Meetings')).toBeLessThan(html.indexOf('JIRAs'))
    expect(html).toContain('Goals')
    expect(html.indexOf('Goals')).toBeLessThan(html.indexOf('Reports'))
    expect(html.indexOf('Reports')).toBeLessThan(html.indexOf('Ledger'))
    expect(html.indexOf('Proposals')).toBeLessThan(html.indexOf('Skills'))
    expect(html.indexOf('Skills')).toBeLessThan(html.indexOf('Webex'))
    expect(html).toContain('Add todo')
    expect(html).toContain('Command palette')
  })
})
