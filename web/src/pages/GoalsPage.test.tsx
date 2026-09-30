import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { GoalsView } from '@/pages/GoalsPage'

describe('goals page', () => {
  it('shows empty state', () => {
    const html = renderToStaticMarkup(
      <GoalsView
        tier="weekly"
        onTier={() => undefined}
        goals={[]}
        heatmap={[]}
        onNew={() => undefined}
        onEdit={() => undefined}
        onArchive={() => undefined}
      />
    )
    expect(html).toContain('No goals yet')
    expect(html).toContain('New goal')
  })

  it('renders goals and drift alert', () => {
    const html = renderToStaticMarkup(
      <GoalsView
        tier="weekly"
        onTier={() => undefined}
        goals={[
          { id: 1, tier: 'weekly', title: 'Ship automation', keywords: ['automation'], status: 'active' },
        ]}
        heatmap={[
          { goal_id: 1, ledger_count: 0, todo_count: 0, top_refs: [] },
        ]}
        onNew={() => undefined}
        onEdit={() => undefined}
        onArchive={() => undefined}
      />
    )
    expect(html).toContain('Ship automation')
    expect(html).toContain('Drift alert')
    expect(html).toContain('Heatmap · last 7 days')
  })
})
