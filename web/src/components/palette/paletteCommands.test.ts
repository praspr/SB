import { describe, expect, it } from 'vitest'
import {
  buildSlashRoute,
  isUrlLikeQuery,
  matchSlashCommands,
  parseSlashInput,
  runBriefReport,
  SLASH_COMMANDS,
} from '@/components/palette/paletteCommands'

describe('parseSlashInput', () => {
  it('splits a command with no argument', () => {
    expect(parseSlashInput('/brief')).toEqual({ cmd: '/brief', arg: '' })
  })

  it('splits a command with an argument', () => {
    expect(parseSlashInput('/ledger apisix outage')).toEqual({ cmd: '/ledger', arg: 'apisix outage' })
  })

  it('trims leading whitespace', () => {
    expect(parseSlashInput('  /wrap')).toEqual({ cmd: '/wrap', arg: '' })
  })
})

describe('matchSlashCommands', () => {
  it('returns nothing for a query that does not start with /', () => {
    expect(matchSlashCommands('plan')).toEqual([])
  })

  it('returns all commands for a bare slash', () => {
    expect(matchSlashCommands('/')).toHaveLength(SLASH_COMMANDS.length)
  })

  it('narrows to a prefix match', () => {
    const matches = matchSlashCommands('/w')
    expect(matches.map((m) => m.cmd)).toEqual(['/wrap'])
  })

  it('matches exactly one command once an argument is typed', () => {
    const matches = matchSlashCommands('/ledger apisix')
    expect(matches.map((m) => m.cmd)).toEqual(['/ledger'])
  })

  it('returns no matches for an unknown command', () => {
    expect(matchSlashCommands('/nonexistent')).toEqual([])
  })
})

describe('buildSlashRoute', () => {
  it('maps /plan to the daily report route', () => {
    expect(buildSlashRoute('/plan', '')).toBe('/reports?template=daily')
  })

  it('maps /wrap to the wrap report route', () => {
    expect(buildSlashRoute('/wrap', '')).toBe('/reports?template=wrap')
  })

  it('maps /standup to the standup report route', () => {
    expect(buildSlashRoute('/standup', '')).toBe('/reports?template=standup')
  })

  it('maps /goals and /attention to their pages', () => {
    expect(buildSlashRoute('/goals', '')).toBe('/goals')
    expect(buildSlashRoute('/attention', '')).toBe('/attention')
  })

  it('maps /ledger <q> to an encoded ledger search route', () => {
    expect(buildSlashRoute('/ledger', 'apisix outage')).toBe('/ledger?q=apisix%20outage')
  })

  it('returns null for /brief (handled inline, not via route)', () => {
    expect(buildSlashRoute('/brief', '')).toBeNull()
  })
})

describe('isUrlLikeQuery', () => {
  it('detects https URLs', () => {
    expect(isUrlLikeQuery('https://cisco-cxe.atlassian.net/browse/CXP-1')).toBe(true)
  })

  it('detects webexteams deep links', () => {
    expect(isUrlLikeQuery('webexteams://im?space=abc')).toBe(true)
  })

  it('detects file URIs', () => {
    expect(isUrlLikeQuery('file:///Users/x/CHANGELOG.md')).toBe(true)
  })

  it('returns false for a plain search query', () => {
    expect(isUrlLikeQuery('what did I ship last week')).toBe(false)
  })

  it('trims whitespace before testing', () => {
    expect(isUrlLikeQuery('   https://example.com  ')).toBe(true)
  })
})

describe('runBriefReport (/brief inline execution, mocked reportDaily)', () => {
  it('returns the markdown from a successful reportDaily call', async () => {
    const markdown = await runBriefReport(async () => ({ markdown: '# Plan\n- do the thing' }))
    expect(markdown).toBe('# Plan\n- do the thing')
  })

  it('falls back to the result error when markdown is empty', async () => {
    const markdown = await runBriefReport(async () => ({ error: 'no plan yet' }))
    expect(markdown).toBe('no plan yet')
  })

  it('falls back to a generic message when both markdown and error are empty', async () => {
    const markdown = await runBriefReport(async () => ({}))
    expect(markdown).toBe('No brief available.')
  })

  it('converts a thrown error into a display message', async () => {
    const markdown = await runBriefReport(async () => {
      throw new Error('sb-core unreachable')
    })
    expect(markdown).toBe('sb-core unreachable')
  })

  it('handles a non-Error throw with a generic message', async () => {
    const markdown = await runBriefReport(async () => {
      throw 'boom'
    })
    expect(markdown).toBe('Could not run brief.')
  })
})
