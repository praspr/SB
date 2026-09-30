import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { WrapView } from '@/pages/WrapPage'

describe('wrap page', () => {
  it('shows the wrap and a pending proposal', () => {
    const html = renderToStaticMarkup(
      <WrapView
        wrap={{
          date: '2026-09-30',
          wrap_md: '- Shipped it [signal:4]',
          dry_run: false,
          persisted: true,
          proposals: [],
        }}
        proposals={[
          {
            id: 7,
            type: 'changelog',
            title: 'CHANGELOG update for 2026-09-30',
            status: 'pending',
            payload: '- Shipped it [signal:4]\n',
          },
        ]}
        wrapping={false}
        onWrap={() => undefined}
        onApprove={() => undefined}
        onReject={() => undefined}
      />,
    )
    expect(html).toContain('[signal:4]')
    expect(html).toContain('CHANGELOG update')
    expect(html).toContain('Approve')
    expect(html).toContain('Reject')
  })

  it('shows the empty state and an error', () => {
    const html = renderToStaticMarkup(
      <WrapView
        proposals={[]}
        error="Could not load wrap."
        wrapping={true}
        onWrap={() => undefined}
        onApprove={() => undefined}
        onReject={() => undefined}
      />,
    )
    expect(html).toContain('No wrap yet.')
    expect(html).toContain('No pending proposals.')
    expect(html).toContain('Could not load wrap.')
    expect(html).toContain('Wrapping')
  })
})
