import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { ToastPortal, ToastStack } from '@/components/shell/ToastPortal'
import { useToast } from '@/lib/useToast'

vi.mock('@radix-ui/react-portal', () => ({
  Root: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe('ToastPortal', () => {
  it('renders the toast stack presenter', () => {
    const html = renderToStaticMarkup(
      <ToastStack queue={[{ id: 1, kind: 'success', message: 'Saved report' }]} dismiss={() => undefined} />,
    )
    expect(html).toContain('Saved report')
  })

  it('renders queued toasts when present', () => {
    const html = renderToStaticMarkup(
      <ToastPortal items={[{ id: 1, kind: 'success', message: 'Saved report', timeout_ms: 3000 }]} onDismiss={() => undefined} />,
    )
    expect(html).toContain('Saved report')
  })
})
