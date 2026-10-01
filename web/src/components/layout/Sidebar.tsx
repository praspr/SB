import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ListTodo, Calendar, MessageSquare, Ticket, Library, ChevronLeft, ChevronRight, Settings, FileText, BookOpen, Inbox, Target, Plus, Command } from 'lucide-react'
import { SettingsPopover } from '@/components/layout/SettingsPopover'
import { webexAttentionRanked } from '@/lib/triage'
import { useUiStore } from '@/lib/store'
import { cn } from '@/lib/utils'

const navGroups = [
  {
    label: 'DO NOW',
    items: [
      { to: '/attention', label: 'Attention', icon: Inbox, end: false },
      { to: '/todos', label: 'Todos', icon: ListTodo, end: false },
      { to: '/meetings', label: 'Meetings', icon: Calendar, end: false },
      { to: '/jira', label: 'JIRAs', icon: Ticket, end: false },
    ],
  },
  {
    label: 'THINK',
    items: [
      { to: '/goals', label: 'Goals', icon: Target, end: false },
      { to: '/reports', label: 'Reports', icon: FileText, end: false },
      { to: '/ledger', label: 'Ledger', icon: BookOpen, end: false },
    ],
  },
  {
    label: 'SYSTEM',
    items: [
      { to: '/proposals', label: 'Proposals', icon: Inbox, end: false },
      { to: '/skills', label: 'Skills', icon: Library, end: false },
      { to: '/webex', label: 'Webex', icon: MessageSquare, end: false },
    ],
  },
]

export function Sidebar() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)
  const openAddTodo = useUiStore((s) => s.openAddTodo)
  const setCommandPaletteOpen = useUiStore((s) => s.setCommandPaletteOpen)
  const attention = useQuery({
    queryKey: ['triage', 'attention', 'sidebar'],
    queryFn: () => webexAttentionRanked(30),
    staleTime: 60_000,
  })
  const unreadCount = attention.data?.length ?? 0

  return (
    <aside
      className={cn(
        'flex h-screen shrink-0 flex-col border-r border-border-subtle bg-bg-panel/90 backdrop-blur transition-[width] duration-base ease-out',
        collapsed ? 'w-[68px]' : 'w-[240px]'
      )}
    >
      <div className="flex items-center gap-3 border-b border-border-subtle px-4 py-4">
        <NavLink
          to="/"
          end
          className={cn(
            'flex min-w-0 items-center gap-3 rounded-lg focus:outline-none focus:ring-1 focus:ring-border-strong hover:bg-bg-elevated',
            collapsed ? 'justify-center p-0' : 'flex-1 px-1.5 py-1',
            'cursor-pointer no-underline'
          )}
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border-strong bg-gradient-to-br from-accent-500/40 to-accent-800 text-13 font-semibold text-white">
            sb
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="truncate text-14 font-semibold text-text-primary">Second Brain</div>
              <div className="truncate text-12 text-text-muted">Chief of Staff</div>
            </div>
          )}
        </NavLink>
        <button
          type="button"
          onClick={toggleSidebar}
          className="ml-auto hidden shrink-0 rounded-md p-1 text-text-muted hover:bg-bg-elevated hover:text-text-primary md:flex"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <nav className="flex-1 px-2.5 py-4">
        {navGroups.map((group, groupIndex) => (
          <div key={group.label} className={cn(groupIndex > 0 && 'mt-4 border-t border-border-subtle pt-4')}>
            {!collapsed ? (
              <div className="px-2.5 pb-2 text-11 uppercase tracking-[0.18em] text-text-muted">{group.label}</div>
            ) : null}
            <div className="space-y-1">
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-2.5 py-2 text-13 font-medium text-text-secondary transition-colors duration-fast ease-out hover:bg-bg-elevated hover:text-text-primary',
                      isActive && 'border border-border-strong bg-accent-500/15 text-text-primary',
                      collapsed && 'justify-center px-0'
                    )
                  }
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon size={18} className="shrink-0" />
                  {!collapsed && (
                    <>
                      <span>{item.label}</span>
                      {item.to === '/attention' && unreadCount > 0 ? (
                        <span className="ml-auto rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 tabular text-text-secondary">
                          {unreadCount}
                        </span>
                      ) : null}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="space-y-1 border-t border-border-subtle px-2.5 py-3">
        <button
          type="button"
          onClick={() => openAddTodo()}
          title="Add todo"
          className={cn(
            'flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-13 font-medium text-text-secondary transition hover:bg-bg-elevated hover:text-text-primary',
            collapsed && 'justify-center px-0',
          )}
        >
          <Plus size={18} className="shrink-0" />
          {!collapsed && (
            <>
              <span>Add todo</span>
              <span className="ml-auto text-12 text-text-muted">⌘N</span>
            </>
          )}
        </button>
        <button
          type="button"
          onClick={() => setCommandPaletteOpen(true)}
          title="Command palette"
          className={cn(
            'flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-13 font-medium text-text-secondary transition hover:bg-bg-elevated hover:text-text-primary',
            collapsed && 'justify-center px-0',
          )}
        >
          <Command size={18} className="shrink-0" />
          {!collapsed && (
            <>
              <span>Command palette</span>
              <span className="ml-auto text-12 text-text-muted">⌘K</span>
            </>
          )}
        </button>
        <div className={cn('pt-1', collapsed ? 'flex justify-center' : 'flex justify-end')}>
          <SettingsPopover>
            <button
              type="button"
              aria-label="Open settings"
              title="Settings"
              className="inline-flex items-center justify-center rounded-md p-1.5 text-text-muted transition-colors duration-fast ease-out hover:bg-bg-elevated hover:text-text-primary"
            >
              <Settings size={16} />
            </button>
          </SettingsPopover>
        </div>
      </div>
    </aside>
  )
}
