import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { MorningBriefView } from '@/components/landing/MorningBrief'

describe('morning brief', () => {
  it('renders the reopen button when hidden', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <MorningBriefView
          dateLabel="Wednesday, September 30"
          open={false}
          meetings={[]}
          tasks={[]}
          deltas={[]}
          threads={[]}
          onDismiss={() => undefined}
          onOpen={() => undefined}
          onGenerateReport={() => undefined}
          onCloseReport={() => undefined}
        />
      </MemoryRouter>
    )
    expect(html).toContain("Show today&#x27;s brief")
  })

  it('renders the four briefing sections when open', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <MorningBriefView
          dateLabel="Wednesday, September 30"
          open
          meetings={[{ id: 'm1', title: 'Standup', start: '2026-09-30T09:00:00Z', end: '2026-09-30T09:30:00Z', attendees: [], is_organizer: false }]}
          tasks={[{ id: 1, title: 'Ship portal', priority: 1, is_completed: false, domain: 'work', source: 'manual' }]}
          deltas={[{ id: 4, ts: '2026-09-30T04:00:00Z', session_id: 's', project: 'sb', action_verb: 'Shipped', summary: 'Shipped portal', body: '', refs: [], source_harness: 'web', origin: 'ledger_log', redaction_applied: false }]}
          threads={[{ id: 5, ts: '2026-09-30T05:00:00Z', session_id: 's', project: 'sb', action_verb: 'Tracked', summary: 'Followed open thread', body: '', refs: [], source_harness: 'web', origin: 'ledger_log', redaction_applied: false, open_refs: [] }]}
          onDismiss={() => undefined}
          onOpen={() => undefined}
          onGenerateReport={() => undefined}
          onCloseReport={() => undefined}
        />
      </MemoryRouter>
    )
    expect(html).toContain('Morning Brief · Wednesday, September 30')
    expect(html).toContain('Meetings today')
    expect(html).toContain('Top todos')
    expect(html).toContain('Overnight ledger deltas')
    expect(html).toContain('Open threads')
  })
})
