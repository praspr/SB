import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { LedgerPageView } from '@/pages/LedgerPage'

describe('ledger page', () => {
  it('renders the ledger shell', () => {
    const html = renderToStaticMarkup(
      <LedgerPageView
        projects={[]}
        project=""
        onProject={() => undefined}
        sourceHarness=""
        onSourceHarness={() => undefined}
        sessionId=""
        onSessionId={() => undefined}
        sessions={[]}
        search=""
        onSearch={() => undefined}
        since=""
        onSince={() => undefined}
        until=""
        onUntil={() => undefined}
        verbs={[]}
        selectedVerbs={[]}
        onToggleVerb={() => undefined}
        view="timeline"
        onView={() => undefined}
        harnesses={[]}
        entries={[]}
        evidenceSignals={[]}
        evidenceStates={[]}
        evidenceQuery=""
        onEvidenceQuery={() => undefined}
        onEvidenceSync={() => undefined}
        selectedEntry={null}
        onSelectEntry={() => undefined}
        onLoadOlder={() => undefined}
      />
    )
    expect(html).toContain('Ledger')
    expect(html).toContain('timeline')
    expect(html).toContain('evidence')
    expect(html).toContain('Load older')
  })
})
