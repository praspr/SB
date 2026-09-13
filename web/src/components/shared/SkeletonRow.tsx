import { cn } from '@/lib/utils'

export type SkeletonRowProps = {
  lines?: number
  compact?: boolean
}

export function SkeletonRow({ lines = 3, compact }: SkeletonRowProps) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={cn(
            'animate-pulse rounded-lg border border-border-subtle bg-bg-panel',
            compact ? 'h-9' : 'h-14'
          )}
        />
      ))}
    </div>
  )
}
