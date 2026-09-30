import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { TodayView } from '@/pages/TodayPage'

describe('today page', () => {
  it('shows the plan and goals', () => {
    const html = renderToStaticMarkup(
      <TodayView
        plan={{ date: '2026-09-30', plan_md: '# Plan\n1. Ship the release' }}
        goals={{ contractual: [{ title: 'Keep the gate green' }], quarterly: [], weekly: [] }}
        planning={false}
        onPlan={() => undefined}
      />,
    )
    expect(html).toContain('Ship the release')
    expect(html).toContain('Keep the gate green')
    expect(html).toContain('Plan day')
  })

  it('shows an empty plan and an error', () => {
    const html = renderToStaticMarkup(
      <TodayView
        goals={{ contractual: [], quarterly: [], weekly: [] }}
        error="Could not load today."
        planning={true}
        onPlan={() => undefined}
      />,
    )
    expect(html).toContain('No plan yet.')
    expect(html).toContain('No active goals.')
    expect(html).toContain('Could not load today.')
    expect(html).toContain('Planning')
  })
})
