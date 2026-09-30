import { describe, expect, it } from 'vitest'
import { usageArc } from './usage-pie'

describe('usage pie', () => {
  it('splits a circle into used and remaining arcs', () => {
    expect(usageArc(25, 100)).toEqual({ used: 0.25, remaining: 0.75, percent: 25 })
  })

  it('caps a full or over-quota chart at the circle', () => {
    expect(usageArc(120, 100)).toEqual({ used: 1, remaining: 0, percent: 120 })
  })

  it('shows an empty chart when the quota is unknown', () => {
    expect(usageArc(null, null)).toEqual({ used: 0, remaining: 1, percent: null })
  })
})
