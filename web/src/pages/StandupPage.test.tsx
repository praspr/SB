import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { standupText } from '@/lib/standup'
import { StandupView } from '@/pages/StandupPage'

describe('standup page', () => {
  it('lists the bullets and a copy action', () => {
    const bullets = [
      'Standup for 2026-09-30.',
      "Yesterday's wrap is recorded.",
      'P1 in progress: Ship the release.',
      'Focus is on planned must-dos.',
      'Evidence is tracked via local signals.',
    ]
    const html = renderToStaticMarkup(
      <StandupView
        standup={{ date: '2026-09-30', bullets }}
        copied={false}
        onCopy={() => undefined}
      />,
    )
    expect(html).toContain('wrap is recorded.')
    expect(html).toContain('Ship the release')
    expect(html).toContain('Copy')
    expect(html.toLowerCase()).not.toContain('blocker')
    expect(standupText(bullets).split('\n')).toHaveLength(5)
  })

  it('shows the empty state and an error', () => {
    const html = renderToStaticMarkup(
      <StandupView error="Could not load standup." copied={false} onCopy={() => undefined} />,
    )
    expect(html).toContain('No standup yet.')
    expect(html).toContain('Could not load standup.')
  })
})
