import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { statusPhase, type CoreStatus } from '@/lib/status'
import { StatusView } from '@/pages/StatusPage'

const ready: CoreStatus = {
  status: 'ok',
  version: '0.1.0',
  database: { ready: true, schema_version: 1, path: 'core.db' },
  counts: { tools: 1, prompts: 0, resources: 0 },
}

describe('status page', () => {
  it('shows a connected core with schema version and counts', () => {
    expect(statusPhase(ready, false)).toBe('connected')
    const html = renderToStaticMarkup(
      <StatusView
        phase="connected"
        data={ready}
        refreshedLabel="2026-09-30 12:00"
        onRetry={() => undefined}
      />,
    )
    expect(html).toContain('connected')
    expect(html).toContain('ready')
    expect(html).toContain('1')
    expect(html).toContain('tools')
    expect(html).toContain('prompts')
    expect(html).toContain('resources')
    expect(html).toContain('2026-09-30 12:00')
    expect(html).toContain('Retry')
  })

  it('shows a degraded state when the database or MCP call fails', () => {
    const degraded: CoreStatus = {
      ...ready,
      status: 'degraded',
      database: { ready: false, schema_version: null },
    }
    expect(statusPhase(undefined, true)).toBe('degraded')
    expect(statusPhase(degraded, false)).toBe('degraded')
    const html = renderToStaticMarkup(
      <StatusView
        phase="degraded"
        data={degraded}
        detail="MCP is unreachable or returned an error."
        refreshedLabel="not yet"
        onRetry={() => undefined}
      />,
    )
    expect(html).toContain('degraded')
    expect(html).toContain('not ready')
    expect(html).toContain('MCP is unreachable or returned an error.')
    expect(html).toContain('Retry')
  })
})
