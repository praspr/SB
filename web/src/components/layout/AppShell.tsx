import { lazy, Suspense, useEffect, useState } from 'react'
import { useLocation, useNavigate, useOutlet } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { useUiStore } from '@/lib/store'
import { SkeletonRow } from '@/components/shared/SkeletonRow'
import { ToastPortal } from '@/components/shell/ToastPortal'
import { AddTodoDialog } from '@/components/tasks/AddTodoDialog'

const CommandPalette = lazy(() => import('@/components/palette/CommandPalette').then((module) => ({ default: module.CommandPalette })))

const titles: Record<string, { title: string; subtitle?: string }> = {
  '/': { title: 'Today', subtitle: 'Your todos, meetings, and quick actions' },
  '/reports': { title: 'Reports', subtitle: 'Daily, weekly, monthly, and query rollups over the ledger' },
  '/ledger': { title: 'Ledger', subtitle: 'Append-only activity and session context across projects' },
  '/proposals': { title: 'Proposals', subtitle: 'Review pending drafted changes before they write locally' },
  '/todos': { title: 'Todos', subtitle: 'Full task list, filterable by status and priority' },
  '/jira': { title: 'JIRAs', subtitle: 'Assigned tickets across your projects' },
  '/meetings': { title: 'Meetings', subtitle: 'Today and the next 7 days' },
  '/webex': { title: 'Webex', subtitle: 'DMs, mentions, and active spaces' },
}

export function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const outlet = useOutlet()
  const setSidebarCollapsed = useUiStore((s) => s.setSidebarCollapsed)
  const commandPaletteOpen = useUiStore((s) => s.commandPaletteOpen)
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen)
  const triggerFocusQuickAdd = useUiStore((s) => s.triggerFocusQuickAdd)
  const [commandPaletteLoaded, setCommandPaletteLoaded] = useState(false)

  useEffect(() => {
    if (commandPaletteOpen) setCommandPaletteLoaded(true)
  }, [commandPaletteOpen])

  useEffect(() => {
    function onResize() {
      setSidebarCollapsed(window.innerWidth < 900)
    }
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [setSidebarCollapsed])

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const isMod = e.metaKey || e.ctrlKey
      if (!isMod) return
      if (e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(true)
      } else if (e.key.toLowerCase() === 'n') {
        e.preventDefault()
        navigate('/todos')
        triggerFocusQuickAdd()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [setCommandPaletteOpen, navigate, triggerFocusQuickAdd])

  const meta = titles[location.pathname]

  return (
    <div className="flex h-screen w-full overflow-hidden bg-bg-app text-text-primary">
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col">
        <TopBar title={location.pathname === '/' ? undefined : meta?.title} subtitle={location.pathname === '/' ? undefined : meta?.subtitle} />
        <div className="flex-1 overflow-y-auto px-6 py-6 lg:px-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
            >
              {outlet}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
      <ToastPortal />
      {commandPaletteLoaded ? (
        <Suspense fallback={<SkeletonRow lines={4} />}>
          <CommandPalette />
        </Suspense>
      ) : null}
      <AddTodoDialog />
    </div>
  )
}
