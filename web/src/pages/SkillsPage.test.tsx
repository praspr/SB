import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import type { SkillDetail, SkillSummary } from '@/lib/skills'
import { SkillsView, type SkillFilters } from '@/pages/SkillsPage'

const alpha: SkillSummary = {
  id: 'alpha',
  name: 'Alpha',
  description: 'Plan the day',
  source: 'project',
  modified_at: '2026-09-30T00:00:00Z',
  available: true,
  enabled: true,
  allowed_tools: ['plan_day'],
}

const filters: SkillFilters = { source: 'all', status: 'all', query: '' }

function view(overrides: Partial<Parameters<typeof SkillsView>[0]> = {}) {
  return renderToStaticMarkup(
    <SkillsView
      skills={[alpha]}
      filters={filters}
      onFilters={() => undefined}
      onOpen={() => undefined}
      onClose={() => undefined}
      syncing={false}
      onSync={() => undefined}
      {...overrides}
    />,
  )
}

describe('skills page', () => {
  it('lists a skill with source, availability, and tools', () => {
    const html = view()
    expect(html).toContain('Alpha')
    expect(html).toContain('Plan the day')
    expect(html).toContain('project')
    expect(html).toContain('available')
    expect(html).toContain('plan_day')
    expect(html).toContain('Search skills')
  })

  it('shows an empty filtered list', () => {
    const html = view({ skills: [], filters: { source: 'claude', status: 'available', query: 'missing' } })
    expect(html).not.toContain('Alpha')
    expect(html).toContain('claude')
  })

  it('shows procedure markdown in the detail panel', () => {
    const detail: SkillDetail = { ...alpha, procedure: '1. Read the signals.', content_sha256: 'abc', synced_at: 'now' }
    const html = view({ detail })
    expect(html).toContain('1. Read the signals.')
    expect(html).toContain('Close')
  })

  it('shows sync progress, result, and error', () => {
    expect(view({ syncing: true })).toContain('Syncing skills')
    expect(
      view({ syncResult: { added: 2, updated: 1, unavailable: 0, duplicates: 0 } }),
    ).toContain('2 added, 1 updated, 0 unavailable')
    expect(view({ error: 'Could not load skills.' })).toContain('Could not load skills.')
  })
})

describe('skill client', () => {
  it('calls list, get, and sync tools', async () => {
    vi.resetModules()
    vi.doMock('@/lib/mcp', () => ({ callTool: vi.fn() }))
    const mcp = await import('@/lib/mcp')
    vi.mocked(mcp.callTool).mockResolvedValue([])
    const api = await import('@/lib/skills')
    await api.listSkills({ source: 'project', status: 'available', query: 'plan' })
    await api.getSkill('alpha')
    await api.syncSkills()
    expect(mcp.callTool).toHaveBeenCalledWith('list_skills', {
      source: 'project',
      status: 'available',
      query: 'plan',
    })
    expect(mcp.callTool).toHaveBeenCalledWith('get_skill', { skill_id: 'alpha' })
    expect(mcp.callTool).toHaveBeenCalledWith('sync_skills')
  })
})
