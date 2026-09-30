import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ProposalsView } from '@/pages/ProposalsPage'

describe('proposals page', () => {
  it('shows the empty state', () => {
    const html = renderToStaticMarkup(
      <ProposalsView
        proposals={[]}
        onRefresh={() => undefined}
        onApprove={() => undefined}
        onReject={() => undefined}
      />
    )
    expect(html).toContain('Nothing pending')
    expect(html).toContain('LLM-drafted proposals will show up here.')
  })

  it('renders proposal rows with actions', () => {
    const html = renderToStaticMarkup(
      <ProposalsView
        proposals={[
          {
            id: 4,
            type: 'changelog',
            title: 'Update release notes',
            status: 'pending',
            payload: '- Added the portal',
            created_at: '2026-09-30T10:00:00Z',
          },
        ]}
        onRefresh={() => undefined}
        onApprove={() => undefined}
        onReject={() => undefined}
      />
    )
    expect(html).toContain('Update release notes')
    expect(html).toContain('Accept')
    expect(html).toContain('Reject')
  })
})
