import { describe, expect, it } from 'vitest'
import { formatSystemClock } from './system-clock'

describe('system clock', () => {
  it('shows the weekday, calendar date, and local time', () => {
    expect(formatSystemClock(new Date(2026, 9, 1, 0, 24))).toBe('Thursday, October 1 · 12:24 AM')
  })
})
