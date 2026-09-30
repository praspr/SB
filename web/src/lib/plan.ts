import { callTool } from './mcp'

export type DayPlan = {
  date: string
  plan_md: string | null
  plan_data?: unknown
  wrap_md?: string | null
  cached?: boolean
}

export type Goals = {
  contractual: Array<{ title: string; keywords?: string[]; active?: boolean }>
  quarterly: Array<{ title: string; keywords?: string[]; active?: boolean }>
  weekly: Array<{ title: string; keywords?: string[]; active?: boolean }>
}

export function planDay(date?: string): Promise<DayPlan> {
  return callTool<DayPlan>('plan_day', date ? { date } : {})
}

export function getGoals(): Promise<Goals> {
  return callTool<Goals>('get_goals')
}
