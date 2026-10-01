import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { ReportsView } from '@/pages/ReportsPage'

vi.mock('@/lib/webex-post', () => ({
  listWebexSpaces: () => Promise.resolve([]),
  webexPostMessage: () => Promise.resolve({ posted: true, space_id: 's1', message_type: 'text' }),
}))

function withClient(children: React.ReactNode) {
  const client = new QueryClient()
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

describe('reports page', () => {
  it('shows the empty state before a run', () => {
    const html = renderToStaticMarkup(
      withClient(
        <ReportsView
          template="today"
          onTemplate={() => undefined}
          project=""
          onProject={() => undefined}
          date="2026-09-30"
          onDate={() => undefined}
          month="2026-09"
          onMonth={() => undefined}
          since="2026-09-01"
          until="2026-09-30"
          onSince={() => undefined}
          onUntil={() => undefined}
          query=""
          onQuery={() => undefined}
          perfShape="full"
          onPerfShape={() => undefined}
          perfVoice="first-person"
          onPerfVoice={() => undefined}
          projects={[]}
          recentRuns={[]}
          activeTab="rituals"
          onTabChange={() => undefined}
          onRun={() => undefined}
          onCopy={() => undefined}
          onSave={() => undefined}
          onSaveToCiq={() => undefined}
        />
      )
    )
    expect(html).toContain('Reports')
    expect(html).toContain('Rituals')
    expect(html).toContain('Brief')
    expect(html).toContain('Pick a template and hit Run.')
    expect(html).toContain('Recent runs')
    expect(html).toContain('today')
  })

  it('renders report actions and citations once data exists', () => {
    const html = renderToStaticMarkup(
      withClient(
        <ReportsView
          template="query"
          onTemplate={() => undefined}
          project="sb"
          onProject={() => undefined}
          date="2026-09-30"
          onDate={() => undefined}
          month="2026-09"
          onMonth={() => undefined}
          since="2026-09-01"
          until="2026-09-30"
          onSince={() => undefined}
          onUntil={() => undefined}
          query="release"
          onQuery={() => undefined}
          perfShape="full"
          onPerfShape={() => undefined}
          perfVoice="first-person"
          onPerfVoice={() => undefined}
          projects={[{ project: 'sb' }]}
          report={{ markdown: '# Daily report\n\n- Shipped release [ledger:12]\n', citations: [12] }}
          citedEntries={[
            {
              id: 12,
              ts: '2026-09-30T10:00:00Z',
              session_id: 'sess',
              project: 'sb',
              action_verb: 'Shipped',
              summary: 'Shipped release',
              body: 'More detail',
              refs: [],
              source_harness: 'web',
              origin: 'ledger_log',
              redaction_applied: false,
            },
          ]}
          recentRuns={[{ template: 'query', project: 'sb', label: 'release', at: '9/30/2026, 10:00 AM' }]}
          activeTab="reports"
          onTabChange={() => undefined}
          onRun={() => undefined}
          onCopy={() => undefined}
          onSave={() => undefined}
          onSaveToCiq={() => undefined}
        />
      )
    )
    expect(html).toContain('Copy markdown')
    expect(html).toContain('Reports')
    expect(html).toContain('Save as ledger note')
    expect(html).toContain('Referenced ledger entries')
    expect(html).toContain('ledger:12')
  })

  it('shows the perf check-in template with shape/voice pickers', () => {
    const html = renderToStaticMarkup(
      withClient(
        <ReportsView
          template="perf_checkin"
          onTemplate={() => undefined}
          project=""
          onProject={() => undefined}
          date="2026-09-30"
          onDate={() => undefined}
          month="2026-09"
          onMonth={() => undefined}
          since="2026-09-01"
          until="2026-09-30"
          onSince={() => undefined}
          onUntil={() => undefined}
          query=""
          onQuery={() => undefined}
          perfShape="full"
          onPerfShape={() => undefined}
          perfVoice="first-person"
          onPerfVoice={() => undefined}
          projects={[]}
          recentRuns={[]}
          activeTab="rituals"
          onTabChange={() => undefined}
          onRun={() => undefined}
          onCopy={() => undefined}
          onSave={() => undefined}
          onSaveToCiq={() => undefined}
        />
      )
    )
    expect(html).toContain('Perf check-in')
    expect(html).toContain('Full weekly')
    expect(html).toContain('One improvement')
    expect(html).toContain('First person')
    expect(html).toContain('Third person')
  })

  it('shows the Save to ciq CHANGELOG button for a perf check-in report', () => {
    const html = renderToStaticMarkup(
      withClient(
        <ReportsView
          template="perf_checkin"
          onTemplate={() => undefined}
          project=""
          onProject={() => undefined}
          date="2026-09-30"
          onDate={() => undefined}
          month="2026-09"
          onMonth={() => undefined}
          since="2026-09-01"
          until="2026-09-30"
          onSince={() => undefined}
          onUntil={() => undefined}
          query=""
          onQuery={() => undefined}
          perfShape="full"
          onPerfShape={() => undefined}
          perfVoice="first-person"
          onPerfVoice={() => undefined}
          projects={[]}
          report={{ markdown: '# Weekly check-in\n\nDid good work.', citations: [] }}
          recentRuns={[]}
          activeTab="rituals"
          onTabChange={() => undefined}
          onRun={() => undefined}
          onCopy={() => undefined}
          onSave={() => undefined}
          onSaveToCiq={() => undefined}
        />
      )
    )
    expect(html).toContain('Save to ciq CHANGELOG')
    expect(html).not.toContain('Email draft')
  })
})
