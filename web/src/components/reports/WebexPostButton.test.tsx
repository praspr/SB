import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { buildMailto, WebexPostPopoverBody } from '@/components/reports/WebexPostButton'

describe('buildMailto', () => {
  it('builds a mailto URL with an encoded subject and body', () => {
    const url = buildMailto('2026-09-30', 'Line one\nLine two')
    expect(url.startsWith('mailto:?subject=')).toBe(true)
    expect(url).toContain(encodeURIComponent('Daily wrap 2026-09-30'))
    expect(url).toContain(encodeURIComponent('Line one\nLine two'))
  })

  it('truncates a long body and appends a truncation notice', () => {
    const longBody = 'x'.repeat(9000)
    const url = buildMailto('2026-09-30', longBody)
    const bodyParam = decodeURIComponent(url.split('body=')[1])
    expect(bodyParam.length).toBeLessThan(longBody.length)
    expect(bodyParam).toContain('truncated')
    expect(bodyParam.startsWith('x'.repeat(100))).toBe(true)
  })

  it('does not truncate a short body', () => {
    const shortBody = 'short report content'
    const url = buildMailto('2026-09-30', shortBody)
    const bodyParam = decodeURIComponent(url.split('body=')[1])
    expect(bodyParam).toBe(shortBody)
    expect(bodyParam).not.toContain('truncated')
  })
})

describe('WebexPostPopoverBody', () => {
  it('renders the space picker and post button', () => {
    const html = renderToStaticMarkup(
      <WebexPostPopoverBody
        spaces={[{ id: 's1', name: 'Release room' }]}
        spaceId=""
        onSpaceIdChange={() => undefined}
        onPost={() => undefined}
      />
    )
    expect(html).toContain('Post to Webex')
    expect(html).toContain('Release room')
    expect(html).toContain('Post')
  })

  it('renders a success label after posting', () => {
    const html = renderToStaticMarkup(
      <WebexPostPopoverBody
        spaces={[{ id: 's1', name: 'Release room' }]}
        spaceId="s1"
        onSpaceIdChange={() => undefined}
        onPost={() => undefined}
        successLabel="Posted to Release room"
      />
    )
    expect(html).toContain('Posted to Release room')
  })

  it('renders an inline error on failure', () => {
    const html = renderToStaticMarkup(
      <WebexPostPopoverBody
        spaces={[]}
        spaceId="s1"
        onSpaceIdChange={() => undefined}
        onPost={() => undefined}
        error="Webex is not signed in."
      />
    )
    expect(html).toContain('Webex is not signed in.')
  })
})
