// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest'
import { dueAt, dueIso, isWithinReminderWindow, markFired, reminderStorageKey, wasFired } from './reminders'

describe('reminders', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('computes a reminder timestamp with lead time', () => {
    const at = dueAt({ due_date: '2026-10-01', due_time: '15:30', remind_before_minutes: 15 })
    expect(at?.getFullYear()).toBe(2026)
    expect(at?.getMonth()).toBe(9)
    expect(at?.getDate()).toBe(1)
    expect(at?.getHours()).toBe(15)
    expect(at?.getMinutes()).toBe(15)
  })

  it('returns null when the todo has no due time', () => {
    expect(dueAt({ due_date: '2026-10-01', due_time: undefined, remind_before_minutes: 0 })).toBeNull()
    expect(dueIso({ due_date: '2026-10-01', due_time: undefined, remind_before_minutes: 0 })).toBeNull()
  })

  it('round-trips fired state in localStorage', () => {
    const reminderIso = '2026-10-01T22:30:00.000Z'
    expect(wasFired(7, reminderIso)).toBe(false)
    markFired(7, reminderIso)
    expect(window.localStorage.getItem(reminderStorageKey(7, reminderIso))).toBe('1')
    expect(wasFired(7, reminderIso)).toBe(true)
  })

  it('matches only reminders due in the last minute window', () => {
    const task = { id: 9, due_date: '2026-10-01', due_time: '15:30', remind_before_minutes: 0 }
    expect(isWithinReminderWindow(task, new Date(2026, 9, 1, 15, 30, 30, 0))).toBe(true)
    expect(isWithinReminderWindow(task, new Date(2026, 9, 1, 15, 31, 1, 0))).toBe(false)
    expect(isWithinReminderWindow(task, new Date(2026, 9, 1, 15, 29, 59, 0))).toBe(false)
  })
})
