import { callTool } from './mcp'

export type GoalTier = 'contractual' | 'quarterly' | 'weekly'
export type GoalStatus = 'active' | 'done' | 'archived'

export type Goal = {
  id: number
  tier: GoalTier
  title: string
  description?: string | null
  keywords: string[]
  target_date?: string | null
  status: GoalStatus
  created_at?: string
  updated_at?: string | null
}

export type GoalHeatmapRow = {
  goal_id: number
  ledger_count: number
  todo_count: number
  combined_count?: number
  top_refs: string[]
}

export type GoalAlignment = {
  goal_id: number
  score: number
}

export function listGoalsV2(filters?: { tier?: GoalTier; status?: GoalStatus | '' }): Promise<Goal[]> {
  return callTool<Goal[]>('list_goals_v2', {
    ...(filters?.tier ? { tier: filters.tier } : {}),
    ...(filters?.status ? { status: filters.status } : {}),
  })
}

export function getGoalV2(id: number): Promise<Goal | null> {
  return callTool<Goal | null>('get_goal_v2', { id })
}

export function addGoal(input: {
  tier: GoalTier
  title: string
  description?: string
  keywords?: string[]
  target_date?: string
}): Promise<Goal> {
  return callTool<Goal>('add_goal', input)
}

export function updateGoal(input: {
  id: number
  title?: string
  description?: string
  keywords?: string[]
  target_date?: string
  tier?: GoalTier
  status?: GoalStatus
}): Promise<Goal> {
  return callTool<Goal>('update_goal', input)
}

export function archiveGoal(id: number): Promise<Goal> {
  return callTool<Goal>('archive_goal', { id })
}

export function scoreAlignment(input: { todo_id?: number; ledger_id?: number }): Promise<GoalAlignment[]> {
  return callTool<GoalAlignment[]>('score_alignment', input)
}

export function heatmapLastWeek(): Promise<GoalHeatmapRow[]> {
  return callTool<GoalHeatmapRow[]>('heatmap_last_week')
}
