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

vi.mock('@/lib/ledger', () => ({
  ledgerSearch: () => Promise.resolve([]),
  ledgerProjects: () => Promise.resolve([]),
  ledgerLog: () => Promise.resolve({ id: 1, ts: '2026-09-30T00:00:00Z', redaction_applied: false, was_new: true }),
}))
vi.mock('@/lib/queries', () => ({ fetchTasks: () => Promise.resolve([]), listMeetings: () => Promise.resolve([]), listJiraTickets: () => Promise.resolve([]), useWebexAttention: () => ({ data: [] }) }))
vi.mock('@/lib/skills', () => ({ listSkills: () => Promise.resolve([]) }))
vi.mock('@/lib/reports', () => ({
  reportQuery: () => Promise.resolve({ markdown: '', citations: [] }),
  reportDaily: () => Promise.resolve({ markdown: '# Brief', citations: [] }),
}))
vi.mock('@/lib/url-hints', () => ({ parseUrlHint: () => Promise.resolve({ kind: 'generic', extracted: {}, suggested_action: 'attach_as_ref' }) }))
vi.mock('@/lib/mcp', () => ({ callTool: () => Promise.resolve({}) }))

import { CommandPalette } from '@/components/palette/CommandPalette'
import { PaletteHint } from '@/components/palette/CommandPalette'

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
    expect(html).toContain('Type / for commands')
    expect(html).toContain('Add todo')
  })

  it('renders the reusable palette hint copy', () => {
    const html = renderToStaticMarkup(<PaletteHint text="Type / for commands · paste a URL to log · Esc to close" />)
    expect(html).toContain('Type / for commands · paste a URL to log · Esc to close')
  })
})
