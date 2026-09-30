import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Calendar, FileText, ListTodo, MessageSquare, Search, Sparkles, Ticket, WrapText, BookOpen } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { useUiStore } from '@/lib/store'
import { ledgerSearch } from '@/lib/ledger'
import { fetchTasks, listJiraTickets } from '@/lib/queries'
import { listSkills } from '@/lib/skills'
import { reportQuery } from '@/lib/reports'
import { useWebexAttention } from '@/lib/queries'

type PaletteItem = {
  id: string
  group: 'Ledger' | 'Todos' | 'JIRAs' | 'Webex' | 'Skills' | 'Reports'
  label: string
  detail?: string
  route: string
  icon: 'ledger' | 'todo' | 'jira' | 'webex' | 'skill' | 'report'
}

const groupOrder: PaletteItem['group'][] = ['Ledger', 'Todos', 'JIRAs', 'Webex', 'Skills', 'Reports']

function iconFor(kind: PaletteItem['icon']) {
  if (kind === 'ledger') return <BookOpen size={15} />
  if (kind === 'todo') return <ListTodo size={15} />
  if (kind === 'jira') return <Ticket size={15} />
  if (kind === 'webex') return <MessageSquare size={15} />
  if (kind === 'report') return <FileText size={15} />
  return <Sparkles size={15} />
}

export function CommandPalette() {
  const navigate = useNavigate()
  const open = useUiStore((s) => s.commandPaletteOpen)
  const setOpen = useUiStore((s) => s.setCommandPaletteOpen)
  const triggerFocusQuickAdd = useUiStore((s) => s.triggerFocusQuickAdd)
  const webexAttention = useWebexAttention()
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 150)
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (!open) {
      setQuery('')
      setDebouncedQuery('')
      setActiveIndex(0)
    }
  }, [open])

  const ledger = useQuery({
    queryKey: ['palette', 'ledger', debouncedQuery],
    queryFn: () => ledgerSearch({ q: debouncedQuery || undefined, limit: 8 }),
    enabled: open,
    staleTime: 15_000,
  })

  const todos = useQuery({
    queryKey: ['palette', 'todos', debouncedQuery],
    queryFn: async () => {
      const rows = await fetchTasks()
      const q = debouncedQuery.toLowerCase()
      return q ? rows.filter((task) => task.title.toLowerCase().includes(q)).slice(0, 8) : rows.slice(0, 8)
    },
    enabled: open,
    staleTime: 15_000,
  })

  const jiras = useQuery({
    queryKey: ['palette', 'jira', debouncedQuery],
    queryFn: () => listJiraTickets({ q: debouncedQuery || undefined, limit: 8 }),
    enabled: open,
    staleTime: 15_000,
  })

  const skills = useQuery({
    queryKey: ['palette', 'skills', debouncedQuery],
    queryFn: () => listSkills(debouncedQuery ? { query: debouncedQuery } : undefined),
    enabled: open,
    staleTime: 15_000,
  })

  const reports = useQuery({
    queryKey: ['palette', 'reports', debouncedQuery],
    queryFn: async () => {
      if (!debouncedQuery) return []
      const result = await reportQuery({ q: debouncedQuery })
      return result.citations.slice(0, 5).map((id) => ({ id, markdown: result.markdown }))
    },
    enabled: open && debouncedQuery.length > 0,
    staleTime: 15_000,
  })

  const items = useMemo<PaletteItem[]>(() => {
    const combined: PaletteItem[] = []

    combined.push(...(ledger.data ?? []).map((entry): PaletteItem => ({
      id: `ledger-${entry.id}`,
      group: 'Ledger',
      label: entry.summary,
      detail: `${entry.project} · ${entry.action_verb}`,
      route: `/ledger?entry=${entry.id}`,
      icon: 'ledger',
    })))

    combined.push(...(todos.data ?? []).map((task): PaletteItem => ({
      id: `todo-${task.id}`,
      group: 'Todos',
      label: task.title,
      detail: `priority ${task.priority}`,
      route: `/todos`,
      icon: 'todo',
    })))

    combined.push(...(jiras.data ?? []).map((ticket): PaletteItem => ({
      id: `jira-${ticket.key}`,
      group: 'JIRAs',
      label: `${ticket.key} · ${ticket.title}`,
      detail: ticket.status,
      route: `/jira?q=${encodeURIComponent(ticket.key)}`,
      icon: 'jira',
    })))

    combined.push(...((webexAttention.data ?? []).slice(0, 8)).map((message): PaletteItem => ({
      id: `webex-${message.id}`,
      group: 'Webex',
      label: message.preview,
      detail: message.space,
      route: '/webex',
      icon: 'webex',
    })))

    combined.push(...(skills.data ?? []).slice(0, 8).map((skill): PaletteItem => ({
      id: `skill-${skill.id}`,
      group: 'Skills',
      label: skill.name,
      detail: skill.description,
      route: `/skills`,
      icon: 'skill',
    })))

    combined.push(...(reports.data ?? []).map((item): PaletteItem => ({
      id: `report-${item.id}`,
      group: 'Reports',
      label: `Report citation ledger:${item.id}`,
      detail: debouncedQuery,
      route: `/reports`,
      icon: 'report',
    })))

    return combined
  }, [debouncedQuery, jiras.data, ledger.data, reports.data, skills.data, todos.data, webexAttention.data])

  useEffect(() => {
    if (activeIndex >= items.length) setActiveIndex(0)
  }, [activeIndex, items.length])

  function close() {
    setOpen(false)
  }

  function run(item: PaletteItem) {
    navigate(item.route)
    close()
  }

  const body = (
    <div
      onKeyDown={(event) => {
        if (event.key === 'ArrowDown') {
          event.preventDefault()
          setActiveIndex((index) => Math.min(items.length - 1, index + 1))
        } else if (event.key === 'ArrowUp') {
          event.preventDefault()
          setActiveIndex((index) => Math.max(0, index - 1))
        } else if (event.key === 'Enter' && items[activeIndex]) {
          event.preventDefault()
          run(items[activeIndex])
        }
      }}
    >
      <div className="flex items-center gap-3 border-b border-border-subtle px-4 py-3.5">
        <Search size={16} className="text-text-muted" />
        <input
          autoFocus
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search ledger, todos, JIRAs, Webex, skills, and reports"
          className="w-full bg-transparent text-14 text-text-primary outline-none placeholder:text-text-muted"
        />
      </div>

      <div className="max-h-[70vh] overflow-y-auto p-3">
        <button
          type="button"
          onClick={() => {
            navigate('/todos')
            triggerFocusQuickAdd()
            close()
          }}
          className="mb-3 flex w-full items-center gap-2 rounded-lg border border-border-subtle bg-black/20 px-3 py-2 text-left text-13 text-text-primary transition-colors duration-fast ease-out hover:border-border-strong hover:bg-bg-elevated"
        >
          <Calendar size={15} className="text-accent-500" />
          Add todo
        </button>

        {items.length === 0 ? (
          <div className="px-3 py-10 text-center text-13 text-text-muted">No results found.</div>
        ) : groupOrder.map((group) => {
          const groupItems = items.filter((item) => item.group === group)
          if (groupItems.length === 0) return null

          return (
            <section key={group} className="mb-4">
              <div className="px-2 py-1 text-12 uppercase tracking-[0.18em] text-text-muted">{group}</div>
              <div className="mt-1 space-y-1">
                {groupItems.map((item) => {
                  const index = items.findIndex((candidate) => candidate.id === item.id)
                  const active = index === activeIndex
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => run(item)}
                      className={`flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left transition-colors duration-fast ease-out ${active ? 'bg-bg-elevated' : 'hover:bg-bg-elevated/70'}`}
                    >
                      <span className="mt-0.5 text-text-muted">{iconFor(item.icon)}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-13 text-text-primary">{item.label}</span>
                        {item.detail ? <span className="mt-0.5 block truncate text-12 text-text-muted">{item.detail}</span> : null}
                      </span>
                    </button>
                  )
                })}
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )

  if (!open && typeof document === 'undefined') return null

  if (typeof document === 'undefined') {
    return <div className="rounded-xl border border-border-strong bg-bg-panel shadow-md">{body}</div>
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="top-[14vh] max-w-2xl translate-y-0 p-0">
        {body}
      </DialogContent>
    </Dialog>
  )
}
