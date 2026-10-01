import type { Task } from './mock-data'

export type DueBadgeTone = 'muted' | 'warning' | 'danger'

export type DueBadgeState = {
  text: string
  tone: DueBadgeTone
  overdue: boolean
  dueSoon: boolean
}

function localDateAt(dateIso: string, time = '00:00'): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateIso)
  const timeMatch = /^(\d{2}):(\d{2})$/.exec(time)
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2]) - 1
  const day = Number(match[3])
  const hour = timeMatch ? Number(timeMatch[1]) : 0
  const minute = timeMatch ? Number(timeMatch[2]) : 0
  return new Date(year, month, day, hour, minute, 0, 0)
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

function addDays(source: Date, days: number): Date {
  return new Date(source.getFullYear(), source.getMonth(), source.getDate() + days, source.getHours(), source.getMinutes(), 0, 0)
}

function formatMonthDay(date: Date): string {
  return `${date.getMonth() + 1}/${date.getDate()}`
}

export function formatDueBadge(task: Pick<Task, 'due_date' | 'due_time' | 'is_completed'>, now = new Date()): DueBadgeState | null {
  if (!task.due_date) return null

  const dueDate = localDateAt(task.due_date, task.due_time ?? '00:00')
  if (!dueDate) return null

  let text = `Due ${formatMonthDay(dueDate)}`
  if (task.due_time) {
    if (sameDay(dueDate, now)) text = `Due ${task.due_time}`
    else if (sameDay(dueDate, addDays(now, 1))) text = `Due tomorrow ${task.due_time}`
    else text = `Due ${formatMonthDay(dueDate)} ${task.due_time}`
  }

  const overdue = !task.is_completed && Boolean(task.due_time && dueDate.getTime() < now.getTime())
  const dueSoon =
    !task.is_completed &&
    Boolean(task.due_time && dueDate.getTime() >= now.getTime() && dueDate.getTime() - now.getTime() <= 60 * 60 * 1000)

  return {
    text,
    tone: overdue ? 'danger' : dueSoon ? 'warning' : 'muted',
    overdue,
    dueSoon,
  }
}
