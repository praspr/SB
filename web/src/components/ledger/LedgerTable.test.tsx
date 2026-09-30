import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { LedgerTable } from '@/components/ledger/LedgerTable'

describe('ledger table', () => {
  it('renders dense ledger rows', () => {
    const html = renderToStaticMarkup(
      <LedgerTable
        entries={[
          {
            id: 3,
            ts: '2026-09-30T10:00:00Z',
            session_id: 'sess-1',
            project: 'sb',
            action_verb: 'Shipped',
            summary: 'Shipped the ledger page',
            body: null,
            refs: [{ kind: 'jira', value: 'CXP-1' }],
            source_harness: 'web',
            origin: 'ledger_log',
            redaction_applied: false,
          },
        ]}
        onSelect={() => undefined}
      />
    )
    expect(html).toContain('Shipped the ledger page')
    expect(html).toContain('2026-09-30 10:00:00')
    expect(html).toContain('web')
  })
})
