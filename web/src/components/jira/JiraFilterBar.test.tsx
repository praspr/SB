import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { JiraFilterBar, JIRA_PROJECTS } from './JiraFilterBar'

describe('jira filters', () => {
  it('offers FSRE and shows every project selected', () => {
    const html = renderToStaticMarkup(
      <JiraFilterBar
        status="active"
        onStatusChange={() => undefined}
        priority="all"
        onPriorityChange={() => undefined}
        projects={[...JIRA_PROJECTS]}
        onProjectsChange={() => undefined}
        onSearchChange={() => undefined}
      />,
    )
    expect(html).toContain('FSRE')
    expect(html).toContain('CXP')
    expect(html).toContain('CXPL')
    expect(html.match(/checked=""/g)?.length).toBe(3)
    expect(html).toContain('Active')
  })
})