export function usageArc(used: number | null, total: number | null) {
  if (used == null || total == null || total <= 0) {
    return { used: 0, remaining: 1, percent: null }
  }
  const fraction = Math.min(1, Math.max(0, used / total))
  return {
    used: fraction,
    remaining: 1 - fraction,
    percent: (used / total) * 100,
  }
}
