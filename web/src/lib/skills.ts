import { callTool } from './mcp'

export type SkillSummary = {
  id: string
  name: string
  description: string
  source: string
  modified_at: string | null
  available: boolean
  enabled: boolean
  allowed_tools: string[]
}

export type SkillDetail = SkillSummary & {
  procedure: string
  content_sha256: string
  synced_at: string
}

export type SkillSyncResult = {
  added: number
  updated: number
  unavailable: number
  duplicates: number
}

export function listSkills(filters?: {
  source?: string
  status?: string
  query?: string
}): Promise<SkillSummary[]> {
  return callTool<SkillSummary[]>('list_skills', {
    ...(filters?.source && filters.source !== 'all' ? { source: filters.source } : {}),
    ...(filters?.status && filters.status !== 'all' ? { status: filters.status } : {}),
    ...(filters?.query ? { query: filters.query } : {}),
  })
}

export function getSkill(skillId: string): Promise<SkillDetail | null> {
  return callTool<SkillDetail | null>('get_skill', { skill_id: skillId })
}

export function syncSkills(): Promise<SkillSyncResult> {
  return callTool<SkillSyncResult>('sync_skills')
}
