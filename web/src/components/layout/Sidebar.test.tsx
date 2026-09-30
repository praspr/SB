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
  it('links to Goals above Reports', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      </QueryClientProvider>
    )
    expect(html).toContain('Goals')
    expect(html).toContain('href="/goals"')
    expect(html.indexOf('Goals')).toBeLessThan(html.indexOf('Reports'))
    expect(html).toContain('Add todo')
    expect(html).toContain('Command palette')
  })
})
