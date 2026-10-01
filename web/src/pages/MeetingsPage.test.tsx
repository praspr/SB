import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MeetingsPage } from './MeetingsPage'

const mockUseMeetings = vi.fn()
const mockUseSyncWebex = vi.fn()
const mockShowToast = vi.fn()
const capturedButtons: Array<{ children?: React.ReactNode; onClick?: () => void }> = []

vi.mock('@/lib/queries', () => ({
  useMeetings: () => mockUseMeetings(),
  useSyncWebex: () => mockUseSyncWebex(),
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, ...props }: { children?: React.ReactNode; onClick?: () => void }) => {
    capturedButtons.push({ children, onClick })
    return <button {...props}>{children}</button>
  },
}))

vi.mock('@/lib/triage', () => ({
  preMeetingContext: vi.fn(),
  proposeMeetingNotes: vi.fn(),
}))

vi.mock('@/lib/useToast', () => ({
  useToast: (selector: (state: { show: typeof mockShowToast }) => unknown) => selector({ show: mockShowToast }),
}))

vi.mock('@/components/meetings/PreMeetingCard', () => ({
  PreMeetingCard: () => <div>Pre-meeting context</div>,
}))

describe('meetings page', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-01T16:00:00Z'))
    capturedButtons.length = 0
    mockShowToast.mockReset()
    mockUseSyncWebex.mockReturnValue({
      mutate: vi.fn((_vars?: unknown, options?: { onSuccess?: (result: { meetings: number }) => void }) => {
        options?.onSuccess?.({ meetings: 3 })
      }),
      isPending: false,
    })
  })

  it('shows earlier-today items separately, future meetings in day groups, and drops older past meetings', () => {
    mockUseMeetings.mockReturnValue({
      data: [
        {
          id: 'past-today',
          title: 'Retro',
          start: '2026-10-01T13:00:00Z',
          end: '2026-10-01T14:00:00Z',
          attendees: [],
          is_organizer: false,
        },
        {
          id: 'future-today',
          title: 'Design review',
          start: '2026-10-01T18:00:00Z',
          end: '2026-10-01T19:00:00Z',
          attendees: [],
          is_organizer: false,
        },
        {
          id: 'future-tomorrow',
          title: 'Planning',
          start: '2026-10-02T17:00:00Z',
          end: '2026-10-02T18:00:00Z',
          attendees: [],
          is_organizer: false,
        },
        {
          id: 'old-past',
          title: 'Old sync',
          start: '2026-09-29T13:00:00Z',
          end: '2026-09-29T14:00:00Z',
          attendees: [],
          is_organizer: false,
        },
      ],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })

    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MeetingsPage />
      </QueryClientProvider>,
    )

    expect(html).toContain('Earlier today · 1')
    expect(html).toContain('Retro')
    expect(html).toContain('Propose notes')
    expect(html).toContain('Design review')
    expect(html).toContain('Planning')
    expect(html).not.toContain('Old sync')
  })

  it('renders the sync button in the header', () => {
    mockUseMeetings.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })

    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MeetingsPage />
      </QueryClientProvider>,
    )

    expect(html).toContain('Sync meetings')
    expect(html).toContain('No upcoming meetings')
  })

  it('fires the sync mutation from the header button', () => {
    const refetch = vi.fn()
    const mutate = vi.fn((_vars?: unknown, options?: { onSuccess?: (result: { meetings: number }) => void }) => {
      options?.onSuccess?.({ meetings: 3 })
    })
    mockUseMeetings.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch,
    })
    mockUseSyncWebex.mockReturnValue({ mutate, isPending: false })

    const client = new QueryClient()
    renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <MeetingsPage />
      </QueryClientProvider>,
    )

    const syncButton = capturedButtons.find((button) => String(button.children).includes('Sync meetings'))
    expect(syncButton?.onClick).toBeTypeOf('function')
    syncButton?.onClick?.()

    expect(mutate).toHaveBeenCalledTimes(1)
    expect(mockShowToast).toHaveBeenCalledWith({ kind: 'success', message: 'Synced meetings · 3' })
    expect(refetch).toHaveBeenCalledTimes(1)
  })
})
