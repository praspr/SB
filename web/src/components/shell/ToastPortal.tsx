import * as Portal from '@radix-ui/react-portal'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'
import { useToast } from '@/lib/useToast'
import { cn } from '@/lib/utils'
import type { ToastItem } from '@/lib/useToast'

const toastIcon = {
  success: <CheckCircle2 size={16} className="text-success-fg" />,
  error: <AlertCircle size={16} className="text-danger-fg" />,
  info: <Info size={16} className="text-info-fg" />,
}

export function ToastStack({
  queue,
  dismiss,
}: {
  queue: Array<{ id: number; kind: 'success' | 'error' | 'info'; message: string }>
  dismiss: (id: number) => void
}) {
  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[80] flex w-[320px] max-w-[calc(100vw-2rem)] flex-col gap-2">
      <AnimatePresence initial={false}>
        {queue.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, x: 24, scale: 0.96 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 24, scale: 0.96 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className={cn(
              'pointer-events-auto rounded-xl border px-4 py-3 shadow-pop backdrop-blur',
              toast.kind === 'success' && 'border-success-border bg-success-bg',
              toast.kind === 'error' && 'border-danger-border bg-danger-bg',
              toast.kind === 'info' && 'border-info-border bg-info-bg',
            )}
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 shrink-0">{toastIcon[toast.kind]}</span>
              <div className="min-w-0 flex-1 text-13 text-text-primary">{toast.message}</div>
              <button
                type="button"
                onClick={() => dismiss(toast.id)}
                className="focus-ring shrink-0 rounded-md p-1 text-text-muted hover:text-text-primary"
              >
                <X size={14} />
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
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
