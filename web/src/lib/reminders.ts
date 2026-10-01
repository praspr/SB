import type { Task } from './mock-data'

const REMINDER_KEY_PREFIX = 'sb-reminder-fired'

type ReminderTask = Pick<Task, 'id' | 'due_date' | 'due_time' | 'remind_before_minutes'>

function localDateTime(dateIso: string, timeIso: string): Date | null {
  const dateMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateIso)
  const timeMatch = /^(\d{2}):(\d{2})$/.exec(timeIso)
  if (!dateMatch || !timeMatch) return null

  return new Date(
    Number(dateMatch[1]),
    Number(dateMatch[2]) - 1,
    Number(dateMatch[3]),
    Number(timeMatch[1]),
    Number(timeMatch[2]),
    0,
    0,
  )
}

export function dueAt(task: Pick<Task, 'due_date' | 'due_time' | 'remind_before_minutes'>): Date | null {
  if (!task.due_date || !task.due_time) return null

  const due = localDateTime(task.due_date, task.due_time)
  if (!due) return null

  const remindBeforeMinutes = Math.max(0, task.remind_before_minutes ?? 0)
  return new Date(due.getTime() - remindBeforeMinutes * 60_000)
}

export const due_at = dueAt

export function dueIso(task: Pick<Task, 'due_date' | 'due_time' | 'remind_before_minutes'>): string | null {
  const at = dueAt(task)
  return at ? at.toISOString() : null
}

export function reminderStorageKey(taskId: number, reminderIso: string): string {
  return `${REMINDER_KEY_PREFIX}-${taskId}-${reminderIso}`
}

export function wasFired(taskId: number, reminderIso: string): boolean {
  if (typeof window === 'undefined') return false
  return window.localStorage.getItem(reminderStorageKey(taskId, reminderIso)) === '1'
}

export function markFired(taskId: number, reminderIso: string): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(reminderStorageKey(taskId, reminderIso), '1')
}

export function isWithinReminderWindow(task: ReminderTask, now = new Date(), windowMs = 60_000): boolean {
  const at = dueAt(task)
  if (!at) return false
  const delta = now.getTime() - at.getTime()
  return delta >= 0 && delta <= windowMs
}
