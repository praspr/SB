import { callTool } from './mcp'

export type ScheduledRitual = {
  id: number
  name: string
  ritual: string
  args: Record<string, unknown>
  cron: string
  target_dir?: string | null
  enabled: boolean
  last_run_at?: string | null
  last_status?: string | null
  last_error?: string | null
}

export type RunDueSchedulesResult = {
  outcomes: Record<string, { ran: boolean; status?: string; error?: string; reason?: string }>
}

export function addScheduledRitual(input: {
  name: string
  ritual: string
  cron: string
  args?: Record<string, unknown>
  enabled?: boolean
  target_dir?: string
}): Promise<ScheduledRitual> {
  return callTool<ScheduledRitual>('add_scheduled_ritual', input)
}

export function listScheduledRituals(): Promise<ScheduledRitual[]> {
  return callTool<ScheduledRitual[]>('list_scheduled_rituals')
}

export function deleteScheduledRitual(id: number): Promise<{ deleted: boolean; id: number }> {
  return callTool<{ deleted: boolean; id: number }>('delete_scheduled_ritual', { id })
}

export function runDueSchedules(): Promise<RunDueSchedulesResult> {
  return callTool<RunDueSchedulesResult>('run_due_schedules')
}
