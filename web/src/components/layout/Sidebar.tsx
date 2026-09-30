import { NavLink } from 'react-router-dom'
import { Home, ListTodo, Calendar, MessageSquare, Ticket, Activity, Library, Radio, Sun, NotebookPen, Megaphone, ChevronLeft, ChevronRight } from 'lucide-react'
import { useUiStore } from '@/lib/store'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/', label: 'Landing', icon: Home, end: true },
  { to: '/status', label: 'Status', icon: Activity, end: false },
  { to: '/skills', label: 'Skills', icon: Library, end: false },
  { to: '/signals', label: 'Signals', icon: Radio, end: false },
  { to: '/today', label: 'Today', icon: Sun, end: false },
  { to: '/wrap', label: 'Wrap', icon: NotebookPen, end: false },
  { to: '/standup', label: 'Standup', icon: Megaphone, end: false },
  { to: '/todos', label: 'Todos', icon: ListTodo, end: false },
  { to: '/jira', label: 'JIRAs', icon: Ticket, end: false },
  { to: '/meetings', label: 'Meetings', icon: Calendar, end: false },
  { to: '/webex', label: 'Webex', icon: MessageSquare, end: false },
]

export function Sidebar() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)

  return (
    <aside
      className={cn(
        'flex h-screen shrink-0 flex-col border-r border-border-subtle bg-bg-panel/90 backdrop-blur transition-[width] duration-base ease-out',
        collapsed ? 'w-[68px]' : 'w-[240px]'
      )}
    >
      <div className="flex items-center gap-3 border-b border-border-subtle px-4 py-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border-strong bg-gradient-to-br from-accent-500/40 to-accent-800 text-13 font-semibold text-white">
          sb
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="truncate text-14 font-semibold text-text-primary">Second Brain</div>
            <div className="truncate text-12 text-text-muted">Chief of Staff</div>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="ml-auto hidden shrink-0 rounded-md p-1 text-text-muted hover:bg-bg-elevated hover:text-text-primary md:flex"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-2.5 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-2.5 py-2 text-13 font-medium text-text-secondary transition-colors duration-fast ease-out hover:bg-bg-elevated hover:text-text-primary',
                isActive && 'bg-accent-500/15 text-text-primary border border-border-strong',
                collapsed && 'justify-center px-0'
              )
            }
            title={collapsed ? item.label : undefined}
          >
            <item.icon size={18} className="shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border-subtle p-3">
        <div
          className={cn(
            'flex items-center gap-2 rounded-lg border border-border-subtle bg-black/20 px-2.5 py-2 text-12',
            collapsed && 'justify-center'
          )}
        >
          <span className="h-2 w-2 shrink-0 rounded-full bg-success" />
          {!collapsed && (
            <>
              <span className="text-text-muted">sb</span>
              <span className="ml-auto text-text-secondary">mock mode</span>
            </>
          )}
        </div>
      </div>
    </aside>
  )
}
