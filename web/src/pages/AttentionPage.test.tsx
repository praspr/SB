import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { AttentionPage, AttentionView } from '@/pages/AttentionPage'

vi.mock('@/lib/triage', async () => {
  const actual = await vi.importActual<typeof import('@/lib/triage')>('@/lib/triage')
  return {
    ...actual,
    webexAttentionFiltered: vi.fn().mockResolvedValue([]),
    logAttentionToLedger: vi.fn(),
  }
})

describe('attention page', () => {
  it('shows inbox zero', () => {
    const html = renderToStaticMarkup(
      <AttentionView items={[]} toast={null} onLog={async () => undefined} />
    )
    expect(html).toContain('Inbox zero')
    expect(html).toContain('Nothing needs your attention right now.')
  })

  it('groups and renders attention items', () => {
    const html = renderToStaticMarkup(
      <AttentionView
        items={[
          {
            id: 'msg-1',
            space_id: 's1',
            space_name: 'Release room',
            sender_name: 'Ada',
            is_dm: false,
            is_mention: true,
            is_unread: true,
            preview: 'Can you review this?',
            occurred_at: '2026-09-30T10:00:00Z',
            deep_link: 'https://webex.example/msg-1',
            triage_kind: 'mention',
            staleness_hours: 1,
            suggested_action_verb: 'Discussed',
          },
        ]}
        toast={{ id: 12, label: 'ledger:12' }}
        onLog={async () => undefined}
      />
    )
    expect(html).toContain('Mentions')
    expect(html).toContain('Ada')
    expect(html).toContain('Log to ledger')
    expect(html).toContain('Create todo')
    expect(html).toContain('Logged as [ledger:12]')
  })

  it('shows general Webex messages instead of dropping them', () => {
    const html = renderToStaticMarkup(
      <AttentionView
        items={[
          {
            id: 'msg-2',
            space_id: 's2',
            space_name: 'Team room',
            sender_name: 'Bo',
            is_dm: false,
            is_mention: false,
            is_unread: true,
            preview: 'The build finished',
            occurred_at: '2026-09-30T11:00:00Z',
            triage_kind: 'message',
            suggested_action_verb: 'Reviewed',
          },
        ]}
        toast={null}
        onLog={async () => undefined}
      />
    )
    expect(html).toContain('Messages')
    expect(html).toContain('The build finished')
    expect(html).not.toContain('Inbox zero')
  })

  it('groups a reply-to-me item under its own Replies section', () => {
    const html = renderToStaticMarkup(
      <AttentionView
        items={[
          {
            id: 'msg-3',
            space_id: 's1',
            space_name: 'Release room',
            sender_name: 'Ada',
            is_dm: false,
            is_mention: false,
            is_unread: true,
            preview: 'Sounds good, thanks',
            occurred_at: '2026-09-30T12:00:00Z',
            parent_message_id: 'parent-1',
            parent_sender_email: 'me@example.com',
            is_reply_to_me: true,
            triage_kind: 'reply-to-me',
            suggested_action_verb: 'Discussed',
          },
        ]}
        toast={null}
        onLog={async () => undefined}
      />
    )
    expect(html).toContain('Replies')
    expect(html).toContain('Sounds good, thanks')
    expect(html).toContain('reply')
  })

  it('loads filtered attention for the page query', () => {
    const client = new QueryClient()
    const html = renderToStaticMarkup(
      <QueryClientProvider client={client}>
        <AttentionPage />
      </QueryClientProvider>
    )
    expect(html).toContain('Attention Inbox')
  })
})
