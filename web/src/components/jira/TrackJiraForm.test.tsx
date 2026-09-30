import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { TrackJiraForm } from './TrackJiraForm'

describe('track jira form', () => {
  it('stays disabled until there is a key or link', () => {
    const html = renderToStaticMarkup(
      <TrackJiraForm value="" pending={false} message={null} tone={null} onChange={() => undefined} onSubmit={() => undefined} />,
    )
    expect(html).toContain('disabled')
    expect(html).toContain('Track JIRA')
  })

  it('shows a pending state and a tracked result', () => {
    const pending = renderToStaticMarkup(
      <TrackJiraForm value="CXP-1" pending message={null} tone={null} onChange={() => undefined} onSubmit={() => undefined} />,
    )
    expect(pending).toContain('disabled')

    const success = renderToStaticMarkup(
      <TrackJiraForm
        value=""
        pending={false}
        message="Tracking CXP-77"
        tone="ok"
        onChange={() => undefined}
        onSubmit={() => undefined}
      />,
    )
    expect(success).toContain('Tracking CXP-77')
  })

  it('shows an invalid-link error', () => {
    const html = renderToStaticMarkup(
      <TrackJiraForm
        value="https://example.com/browse/CXP-1"
        pending={false}
        message="Only links from the configured Atlassian site are accepted"
        tone="error"
        onChange={() => undefined}
        onSubmit={() => undefined}
      />,
    )
    expect(html).toContain('configured Atlassian site')
  })
})