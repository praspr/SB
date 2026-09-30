import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { UsagePie } from '@/components/landing/UsageStats'

describe('usage pie details', () => {
  it('keeps the full usage breakdown available from the chart', () => {
    const html = renderToStaticMarkup(
      <UsagePie
        label="GitHub Copilot"
        used={30687}
        total={100000}
        details={[
          ['Plan', 'Enterprise'],
          ['Remaining', '69,313'],
          ['Resets', 'Oct 1'],
          ['Chat', 'unlimited'],
        ]}
      />,
    )

    expect(html).toContain('GitHub Copilot')
    expect(html).toContain('role="img"')
    expect(html).toContain('30.7% used')
    expect(html).toContain('Enterprise')
    expect(html).toContain('69,313')
    expect(html).toContain('group-hover:block')
  })
})
