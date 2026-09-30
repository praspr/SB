import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { AttentionView } from '@/pages/AttentionPage'

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
    expect(html).toContain('Logged as [ledger:12]')
  })
})
