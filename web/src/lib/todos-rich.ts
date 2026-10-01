import { callTool } from './mcp'
import type { Task } from './mock-data'

type TodoRow = {
  id: number
  title: string
  description: string
  priority: number
  due_date: string | null
  due_time: string | null
  remind_before_minutes: number | null
  is_completed: boolean
  domain: 'work' | 'learning' | 'personal' | string
  external_source: string | null
  external_ref: string | null
  goal_id: number | null
  jira_ref: string | null
  recurrence_rule: string | null
}

export type RichTask = Task & {
  goal_id?: number | null
  jira_ref?: string | null
  recurrence_rule?: string | null
  remind_before_minutes?: number | null
}

export function toRichTask(row: TodoRow): RichTask {
  return {
    id: row.id,
    title: row.title,
    description: row.description || undefined,
    priority: Math.min(4, Math.max(1, row.priority)) as Task['priority'],
    due_date: row.due_date ?? undefined,
    due_time: row.due_time ?? undefined,
    remind_before_minutes: row.remind_before_minutes,
    is_completed: row.is_completed,
    domain: row.domain === 'learning' || row.domain === 'personal' ? row.domain : 'work',
    source: row.external_source === 'jira' ? 'jira' : row.external_source === 'changelog' ? 'changelog' : 'manual',
    ref: row.external_ref ?? undefined,
    jira_ref: row.jira_ref,
    goal_id: row.goal_id,
    recurrence_rule: row.recurrence_rule,
  }
}

export function fetchRichTasks(): Promise<RichTask[]> {
  return callTool<TodoRow[]>('todo_list', { status: 'all' }).then((rows) => rows.map(toRichTask))
}

export function createRichTask(input: {
  title: string
  description?: string
  priority: Task['priority']
  domain: Task['domain']
  due_date?: string
  due_time?: string
  remind_before_minutes?: number
  external_source?: string
  external_ref?: string
  goal_id?: number
  jira_ref?: string
  recurrence_rule?: string
}): Promise<RichTask> {
  return callTool<TodoRow>('todo_add', input).then(toRichTask)
}
