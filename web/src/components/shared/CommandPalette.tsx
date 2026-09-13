import { Command } from 'cmdk'
import { useNavigate } from 'react-router-dom'
import { useUiStore } from '@/lib/store'
import { ListTodo, Calendar, MessageSquare, Home, PlusCircle, Ticket } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'

export function CommandPalette() {
  const open = useUiStore((s) => s.commandPaletteOpen)
  const setOpen = useUiStore((s) => s.setCommandPaletteOpen)
  const triggerFocusQuickAdd = useUiStore((s) => s.triggerFocusQuickAdd)
  const navigate = useNavigate()

  function run(action: () => void) {
    action()
    setOpen(false)
  }

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] flex items-start justify-center pt-[15vh]">
          <motion.div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={() => setOpen(false)}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ type: 'spring', stiffness: 420, damping: 32 }}
            className="relative z-10 w-full max-w-lg overflow-hidden rounded-xl border border-border-strong bg-bg-panel shadow-md"
          >
            <Command label="Command palette" shouldFilter>
              <Command.Input
                autoFocus
                placeholder="Type a command or search..."
                className="w-full border-b border-border-subtle bg-transparent px-4 py-3.5 text-14 text-text-primary placeholder:text-text-muted outline-none"
              />
              <Command.List className="max-h-80 overflow-y-auto p-2">
                <Command.Empty className="px-3 py-6 text-center text-13 text-text-muted">
                  No results found.
                </Command.Empty>
                <Command.Group heading="Actions" className="px-2 py-1 text-12 uppercase tracking-wide text-text-muted">
                  <Command.Item
                    onSelect={() =>
                      run(() => {
                        navigate('/todos')
                        triggerFocusQuickAdd()
                      })
                    }
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-13 text-text-primary aria-selected:bg-bg-elevated"
                  >
                    <PlusCircle size={16} className="text-accent-500" />
                    Add todo
                  </Command.Item>
                </Command.Group>
                <Command.Group heading="Navigation" className="mt-1 px-2 py-1 text-12 uppercase tracking-wide text-text-muted">
                  <Command.Item
                    onSelect={() => run(() => navigate('/'))}
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-13 text-text-primary aria-selected:bg-bg-elevated"
                  >
                    <Home size={16} /> Go to Landing
                  </Command.Item>
                  <Command.Item
                    onSelect={() => run(() => navigate('/todos'))}
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-13 text-text-primary aria-selected:bg-bg-elevated"
                  >
                    <ListTodo size={16} /> Go to Todos
                  </Command.Item>
                  <Command.Item
                    onSelect={() => run(() => navigate('/jira'))}
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-13 text-text-primary aria-selected:bg-bg-elevated"
                  >
                    <Ticket size={16} /> Go to JIRAs
                  </Command.Item>
                  <Command.Item
                    onSelect={() => run(() => navigate('/meetings'))}
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-13 text-text-primary aria-selected:bg-bg-elevated"
                  >
                    <Calendar size={16} /> Go to Meetings
                  </Command.Item>
                  <Command.Item
                    onSelect={() => run(() => navigate('/webex'))}
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-13 text-text-primary aria-selected:bg-bg-elevated"
                  >
                    <MessageSquare size={16} /> Go to Webex
                  </Command.Item>
                </Command.Group>
              </Command.List>
            </Command>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
