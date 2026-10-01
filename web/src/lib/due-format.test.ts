import { describe, expect, it } from 'vitest'
import { formatDueBadge } from './due-format'

describe('formatDueBadge', () => {
  const now = new Date(2026, 9, 1, 14, 0, 0, 0)

  it('formats today with time compactly', () => {
    expect(formatDueBadge({ due_date: '2026-10-01', due_time: '15:30', is_completed: false }, now)).toEqual(
      expect.objectContaining({ text: 'Due 15:30', tone: 'muted', overdue: false, dueSoon: false }),
    )
  })

  it('formats tomorrow with time', () => {
    expect(formatDueBadge({ due_date: '2026-10-02', due_time: '09:00', is_completed: false }, now)).toEqual(
      expect.objectContaining({ text: 'Due tomorrow 09:00' }),
    )
  })

  it('formats date-only todos without a reminder state', () => {
    expect(formatDueBadge({ due_date: '2026-10-05', is_completed: false }, now)).toEqual(
      expect.objectContaining({ text: 'Due 10/5', tone: 'muted', overdue: false, dueSoon: false }),
    )
  })

  it('marks overdue timed todos as danger', () => {
    expect(formatDueBadge({ due_date: '2026-10-01', due_time: '13:15', is_completed: false }, now)).toEqual(
      expect.objectContaining({ tone: 'danger', overdue: true }),
    )
  })

  it('marks tasks due within an hour as warning', () => {
    expect(formatDueBadge({ due_date: '2026-10-01', due_time: '14:45', is_completed: false }, now)).toEqual(
      expect.objectContaining({ tone: 'warning', dueSoon: true, text: 'Due 14:45' }),
    )
  })
})
