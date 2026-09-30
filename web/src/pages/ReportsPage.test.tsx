import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ReportsView } from '@/pages/ReportsPage'

describe('reports page', () => {
  it('shows the empty state before a run', () => {
    const html = renderToStaticMarkup(
      <ReportsView
        template="daily"
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
        projects={[]}
        recentRuns={[]}
        onRun={() => undefined}
        onCopy={() => undefined}
        onSave={() => undefined}
      />
    )
    expect(html).toContain('Reports')
    expect(html).toContain('Pick a template and hit Run.')
    expect(html).toContain('Recent runs')
  })

  it('renders report actions and citations once data exists', () => {
    const html = renderToStaticMarkup(
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
        onRun={() => undefined}
        onCopy={() => undefined}
        onSave={() => undefined}
      />
    )
    expect(html).toContain('Copy markdown')
    expect(html).toContain('Save as ledger note')
    expect(html).toContain('Referenced ledger entries')
    expect(html).toContain('ledger:12')
  })
})
