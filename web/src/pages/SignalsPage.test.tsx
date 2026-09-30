import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { cite } from '@/lib/signals'
import { SignalsView } from '@/pages/SignalsPage'

describe('signals page', () => {
  it('cites each signal and lists adapter state', () => {
    const html = renderToStaticMarkup(
      <SignalsView
        signals={[{ id: 4, source: 'git', kind: 'commit', occurred_at: '2026-09-30T00:00:00Z', title: 'Fix the gate' }]}
        states={[{ adapter: 'git', last_run_at: '2026-09-30T00:00:00Z', signal_count: 1, error: null }]}
        query=""
        onQuery={() => undefined}
        syncing={false}
        onSync={() => undefined}
      />,
    )
    expect(html).toContain('[signal:4] Fix the gate')
    expect(html).toContain('git: 1 signals')
    expect(cite({ id: 4, source: 'git', kind: 'commit', occurred_at: '', title: 'Fix the gate' })).toBe(
      '[signal:4] Fix the gate',
    )
  })

  it('shows a load error', () => {
    const html = renderToStaticMarkup(
      <SignalsView
        signals={[]}
        states={[]}
        query="gate"
        onQuery={() => undefined}
        syncing={true}
        error="Could not load signals."
        onSync={() => undefined}
      />,
    )
    expect(html).toContain('Could not load signals.')
    expect(html).toContain('Syncing adapters')
  })
})
