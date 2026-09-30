import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/store', () => ({
  useUiStore: (selector: (state: any) => unknown) => selector({
    commandPaletteOpen: true,
    setCommandPaletteOpen: () => undefined,
    triggerFocusQuickAdd: () => undefined,
  }),
}))

vi.mock('@/lib/ledger', () => ({ ledgerSearch: () => Promise.resolve([]) }))
vi.mock('@/lib/queries', () => ({ fetchTasks: () => Promise.resolve([]), listMeetings: () => Promise.resolve([]), listJiraTickets: () => Promise.resolve([]), useWebexAttention: () => ({ data: [] }) }))
vi.mock('@/lib/skills', () => ({ listSkills: () => Promise.resolve([]) }))
vi.mock('@/lib/reports', () => ({ reportQuery: () => Promise.resolve({ markdown: '', citations: [] }) }))

import { CommandPalette } from '@/components/palette/CommandPalette'

describe('command palette', () => {
  it('renders the search shell and action row', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <CommandPalette />
        </MemoryRouter>
      </QueryClientProvider>
    )
    expect(html).toContain('Search ledger, todos, JIRAs, Webex, skills, and reports')
    expect(html).toContain('Add todo')
  })
})
