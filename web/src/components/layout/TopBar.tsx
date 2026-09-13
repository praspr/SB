import { useUiStore } from '@/lib/store'

export function TopBar({ title, subtitle }: { title: string; subtitle?: string }) {
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen)
  const setAddTodoOpen = useUiStore((s) => s.setAddTodoOpen)

  return (
    <header className="sticky top-0 z-20 border-b border-border-subtle bg-bg-app/85 backdrop-blur">
      <div className="flex items-center gap-4 px-6 py-4 lg:px-8">
        <div>
          <div className="text-12 uppercase tracking-[0.16em] text-text-muted">sb dashboard</div>
          <div className="mt-1 text-20 font-semibold tracking-tight text-text-primary">{title}</div>
          {subtitle && <div className="mt-0.5 text-13 text-text-secondary">{subtitle}</div>}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setAddTodoOpen(true)}
            className="hidden items-center gap-2 rounded-lg border border-border-subtle bg-bg-panel px-3 py-2 text-13 text-text-secondary transition hover:border-border-strong hover:text-text-primary md:flex"
          >
            <span className="text-text-muted">⌘N</span>
            <span>Add todo</span>
          </button>
          <button
            onClick={() => setCommandPaletteOpen(true)}
            className="flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-panel px-3 py-2 text-13 text-text-secondary transition hover:border-border-strong hover:text-text-primary"
          >
            <span className="text-text-muted">⌘K</span>
            <span className="hidden sm:inline">Command palette</span>
          </button>
        </div>
      </div>
    </header>
  )
}
