import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { HeatmapGrid } from '@/components/goals/HeatmapGrid'

describe('HeatmapGrid', () => {
  it('renders axis labels, truncated row labels, and the legend', () => {
    const html = renderToStaticMarkup(
      <HeatmapGrid
        goals={[{ id: 1, tier: 'weekly', title: 'Ship the multi-surface launch checklist this week', keywords: [], status: 'active' }]}
        heatmap={[{ goal_id: 1, ledger_count: 2, todo_count: 1, top_refs: [] }]}
      />,
    )

    expect(html).toContain('Weekly activity')
    expect(html).toContain('last 7 days')
    expect(html).toContain('Combined ledger + todo hits')
    expect(html).toContain('healthy')
    expect(html).toContain('Ship the multi-surface l…')
    expect(html).toContain('title="Ship the multi-surface launch checklist this week"')
  })
})
