import { describe, expect, it } from 'vitest'
import type { Task } from './mock-data'
import { organizeTodos, summarizeTodos } from './todo-groups'

const tasks: Task[] = [
  { id: 1, title: 'Overdue P2', priority: 2, due_date: '2026-09-30', is_completed: false, domain: 'work', source: 'manual' },
  { id: 2, title: 'Today P1', priority: 1, due_date: '2026-10-01', is_completed: false, domain: 'work', source: 'jira', jira_ref: 'CXP-2' },
  { id: 3, title: 'Upcoming', priority: 3, due_date: '2026-10-03', is_completed: false, domain: 'personal', source: 'manual' },
  { id: 4, title: 'Someday', priority: 4, is_completed: false, domain: 'learning', source: 'manual' },
  { id: 5, title: 'Finished', priority: 2, due_date: '2026-10-01', is_completed: true, domain: 'work', source: 'manual' },
]

describe('todo organization', () => {
  it('summarizes overdue, today, open, and completed tasks', () => {
    expect(summarizeTodos(tasks, '2026-10-01')).toEqual({
      overdue: 1,
      today: 1,
      open: 4,
      completed: 1,
    })
  })

  it('groups open work into today, upcoming, and no-date sections', () => {
    const result = organizeTodos(tasks, {
      status: 'open',
      priority: 'all',
      query: '',
      sort: 'priority',
      today: '2026-10-01',
    })

    expect(result.map((group) => [group.label, group.tasks.map((task) => task.id)])).toEqual([
      ['Today', [2, 1]],
      ['Upcoming', [3]],
      ['No date', [4]],
    ])
  })

  it('searches metadata and sorts titles', () => {
    const result = organizeTodos(tasks, {
      status: 'all',
      priority: 'all',
      query: 'cxp-2',
      sort: 'title',
      today: '2026-10-01',
    })

    expect(result.flatMap((group) => group.tasks.map((task) => task.id))).toEqual([2])
  })

  it('puts completed-only results in one completed group', () => {
    const result = organizeTodos(tasks, {
      status: 'completed',
      priority: 'all',
      query: '',
      sort: 'due',
      today: '2026-10-01',
    })

    expect(result).toEqual([{ key: 'completed', label: 'Completed', tasks: [tasks[4]] }])
  })
})
