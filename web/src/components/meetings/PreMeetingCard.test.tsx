import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { PreMeetingCard } from '@/components/meetings/PreMeetingCard'

describe('pre-meeting card', () => {
  it('renders meeting context sections', () => {
    const html = renderToStaticMarkup(
      <PreMeetingCard
        context={{
          meeting: {
            id: 'meet-1',
            title: 'Release review',
            start_at: '2026-09-30T10:00:00Z',
            end_at: '2026-09-30T10:30:00Z',
            attendees: [{ name: 'Ada', email: 'ada@example.com' }],
            join_url: 'https://webex.example/meet-1',
          },
          recent_messages: [
            {
              id: 'msg-1',
              space_id: 's1',
              space_name: 'Release room',
              sender_name: 'Ada',
              is_dm: false,
              is_mention: true,
              is_unread: true,
              preview: 'Can you check this?',
              occurred_at: '2026-09-30T09:50:00Z',
              triage_kind: 'mention',
              suggested_action_verb: 'Discussed',
            },
          ],
          recent_ledger: [
            {
              id: 10,
              ts: '2026-09-29T10:00:00Z',
              session_id: 'sess',
              project: 'sb',
              action_verb: 'Reviewed',
              summary: 'Reviewed release notes',
              body: '',
              refs: [],
              source_harness: 'web',
              origin: 'ledger_log',
              redaction_applied: false,
            },
          ],
          related_jiras: ['CXP-1'],
          open_todos: [{ id: 1, title: 'Prep release review', priority: 1 }],
        }}
        onDismiss={() => undefined}
      />
    )
    expect(html).toContain('Pre-meeting context')
    expect(html).toContain('Recent messages')
    expect(html).toContain('Related ledger')
    expect(html).toContain('Suggested actions')
  })
})
