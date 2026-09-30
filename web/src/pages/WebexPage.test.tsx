import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { WebexPage } from './WebexPage'

vi.mock('@/lib/queries', () => ({
  useWebexMessages: () => ({ data: [], isLoading: false, isError: true, error: new Error('offline') }),
  useWebexSpaces: () => ({ data: [], isLoading: false }),
  useWebexAttention: () => ({ data: [], isLoading: false }),
  useWebexStatus: () => ({
    data: { authenticated: false, meetings_count: 0, messages_count: 0, login_path: '/webex/login' },
  }),
  useSyncWebex: () => ({ mutate: () => undefined, isPending: false, data: undefined }),
  summarizeWebexSpace: vi.fn(),
}))

describe('webex page', () => {
  it('shows sign-in and a load error without inventing messages', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <WebexPage />
      </MemoryRouter>,
    )
    expect(html).toContain('Sign in to Webex')
    expect(html).toContain('offline')
    expect(html).toContain('Nothing waiting')
  })
})
