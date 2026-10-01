import * as Portal from '@radix-ui/react-portal'
import { X } from 'lucide-react'
import { useToast } from '@/lib/useToast'
import { cn } from '@/lib/utils'
import type { ToastItem } from '@/lib/useToast'

export function ToastStack({
  queue,
  dismiss,
}: {
  queue: Array<{ id: number; kind: 'success' | 'error' | 'info'; message: string }>
  dismiss: (id: number) => void
}) {
  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[80] flex w-[320px] max-w-[calc(100vw-2rem)] flex-col gap-2">
      {queue.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            'pointer-events-auto rounded-xl border px-4 py-3 shadow-md backdrop-blur',
            toast.kind === 'success' && 'border-success/40 bg-success/10 text-text-primary',
            toast.kind === 'error' && 'border-danger/40 bg-danger/10 text-text-primary',
            toast.kind === 'info' && 'border-info/40 bg-info/10 text-text-primary',
          )}
        >
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1 text-13">{toast.message}</div>
            <button type="button" onClick={() => dismiss(toast.id)} className="rounded-md p-1 text-text-muted hover:text-text-primary">
              <X size={14} />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export function ToastPortal({
  items,
  onDismiss,
}: {
  items?: ToastItem[]
  onDismiss?: (id: number) => void
}) {
  const queue = useToast((s) => s.queue)
  const dismiss = useToast((s) => s.dismiss)
  const visibleToasts = items ?? queue
  const dismissToast = onDismiss ?? dismiss

  if (visibleToasts.length === 0) return null

  if (typeof document === 'undefined') {
    return <ToastStack queue={visibleToasts} dismiss={dismissToast} />
  }

  return (
    <Portal.Root>
      <ToastStack queue={visibleToasts} dismiss={dismissToast} />
    </Portal.Root>
  )
}
