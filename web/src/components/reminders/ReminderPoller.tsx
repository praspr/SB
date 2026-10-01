import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchRichTasks } from '@/lib/todos-rich'
import { dueAt, dueIso, isWithinReminderWindow, markFired, wasFired } from '@/lib/reminders'
import { useToast } from '@/lib/useToast'

const ONE_DAY_MS = 24 * 60 * 60 * 1000

export function ReminderPoller() {
  const { data: tasks } = useQuery({
    queryKey: ['tasks', 'rich'],
    queryFn: fetchRichTasks,
    staleTime: 30_000,
  })
  const showToast = useToast((state) => state.show)

  useEffect(() => {
    function notifyTask(title: string) {
      if (typeof window !== 'undefined' && 'Notification' in window && window.Notification.permission === 'granted') {
        void new window.Notification('sb reminder', { body: title })
      }
      showToast({ kind: 'info', message: `Reminder: ${title}`, timeout_ms: 15_000 })
    }

    function scan(mode: 'mount' | 'tick') {
      const now = new Date()
      for (const task of tasks ?? []) {
        if (task.is_completed) continue
        const taskDueAt = dueAt(task)
        const reminderIso = dueIso(task)
        if (!taskDueAt || !reminderIso) continue
        if (wasFired(task.id, reminderIso)) continue

        if (mode === 'mount') {
          const ageMs = now.getTime() - taskDueAt.getTime()
          if (ageMs > ONE_DAY_MS) {
            markFired(task.id, reminderIso)
            continue
          }
          if (ageMs >= 0) {
            notifyTask(task.title)
            markFired(task.id, reminderIso)
          }
          continue
        }

        if (isWithinReminderWindow(task, now)) {
          notifyTask(task.title)
          markFired(task.id, reminderIso)
        }
      }
    }

    scan('mount')
    const timerId = window.setInterval(() => scan('tick'), 60_000)
    return () => window.clearInterval(timerId)
  }, [showToast, tasks])

  return null
}
