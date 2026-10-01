import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Calendar, FileText, Ticket, ListTodo, MessageSquare, Search, Sparkles, Terminal, Link2, BookOpen } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { useUiStore } from '@/lib/store'
import { ledgerSearch } from '@/lib/ledger'
import { fetchTasks, listJiraTickets } from '@/lib/queries'
import { listSkills } from '@/lib/skills'
import { reportDaily, reportQuery } from '@/lib/reports'
import { useWebexAttention } from '@/lib/queries'
import { parseUrlHint, type UrlHint } from '@/lib/url-hints'
import { callTool } from '@/lib/mcp'
import { AttachRefDialog } from '@/components/palette/AttachRefDialog'
import {
  buildSlashRoute,
  isUrlLikeQuery,
  matchSlashCommands,
  parseSlashInput,
  runBriefReport,
  type SlashCommandDef,
} from '@/components/palette/paletteCommands'

type PaletteItem = {
  id: string
  group: 'Ledger' | 'Todos' | 'JIRAs' | 'Webex' | 'Skills' | 'Reports'
  label: string
  detail?: string
  route: string
  icon: 'ledger' | 'todo' | 'jira' | 'webex' | 'skill' | 'report'
}

const groupOrder: PaletteItem['group'][] = ['Ledger', 'Todos', 'JIRAs', 'Webex', 'Skills', 'Reports']

export function PaletteHint({ text }: { text: string }) {
  return <div className="px-3 py-10 text-center text-13 text-text-muted">{text}</div>
}

function iconFor(kind: PaletteItem['icon']) {
  if (kind === 'ledger') return <BookOpen size={15} />
  if (kind === 'todo') return <ListTodo size={15} />
  if (kind === 'jira') return <Ticket size={15} />
  if (kind === 'webex') return <MessageSquare size={15} />
  if (kind === 'report') return <FileText size={15} />
  return <Sparkles size={15} />
}

function urlHintActionLabel(hint: UrlHint): string {
  if (hint.kind === 'jira') return `Track JIRA ${String(hint.extracted.key ?? '')}`
  if (hint.kind === 'github') return 'Attach as ref to a new ledger note'
  if (hint.kind === 'webex') return 'Open space'
  if (hint.kind === 'file') return 'Attach to ledger'
  return 'Add as ledger ref'
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
  const [briefOpen, setBriefOpen] = useState(false)
  const [briefMarkdown, setBriefMarkdown] = useState('')
  const [briefPending, setBriefPending] = useState(false)
  const [attachRef, setAttachRef] = useState<{ kind: string; value: string; url?: string } | null>(null)

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

  const isSlash = query.startsWith('/')
  const isUrl = isUrlLikeQuery(debouncedQuery)
  const slashMatches = useMemo(() => matchSlashCommands(query), [query])

  const urlHint = useQuery({
    queryKey: ['palette', 'url-hint', debouncedQuery],
    queryFn: () => parseUrlHint(debouncedQuery),
    enabled: open && isUrl,
    staleTime: 15_000,
  })


  const suppressNormalSearch = isSlash || isUrl

  const ledger = useQuery({
    queryKey: ['palette', 'ledger', debouncedQuery],
    queryFn: () => ledgerSearch({ q: debouncedQuery || undefined, limit: 8 }),
    enabled: open && !suppressNormalSearch,
    staleTime: 15_000,
  })

  const todos = useQuery({
    queryKey: ['palette', 'todos', debouncedQuery],
    queryFn: async () => {
      const rows = await fetchTasks()
      const q = debouncedQuery.toLowerCase()
      return q ? rows.filter((task) => task.title.toLowerCase().includes(q)).slice(0, 8) : rows.slice(0, 8)
    },
    enabled: open && !suppressNormalSearch,
    staleTime: 15_000,
  })

  const jiras = useQuery({
    queryKey: ['palette', 'jira', debouncedQuery],
    queryFn: () => listJiraTickets({ q: debouncedQuery || undefined, limit: 8 }),
    enabled: open && !suppressNormalSearch,
    staleTime: 15_000,
  })

  const skills = useQuery({
    queryKey: ['palette', 'skills', debouncedQuery],
    queryFn: () => listSkills(debouncedQuery ? { query: debouncedQuery } : undefined),
    enabled: open && !suppressNormalSearch,
    staleTime: 15_000,
  })

  const reports = useQuery({
    queryKey: ['palette', 'reports', debouncedQuery],
    queryFn: async () => {
      if (!debouncedQuery) return []
      const result = await reportQuery({ q: debouncedQuery })
      return result.citations.slice(0, 5).map((id) => ({ id, markdown: result.markdown }))
    },
    enabled: open && !suppressNormalSearch && debouncedQuery.length > 0,
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

  useEffect(() => {
    setActiveIndex(0)
  }, [isSlash, isUrl])

  function close() {
    setOpen(false)
  }

  function run(item: PaletteItem) {
    navigate(item.route)
    close()
  }

  function runSlashCommand(def: SlashCommandDef, arg: string) {
    if (def.kind === 'brief') {
      setBriefOpen(true)
      setBriefPending(true)
      setBriefMarkdown('')
      close()
      void runBriefReport(reportDaily).then((markdown) => {
        setBriefMarkdown(markdown)
        setBriefPending(false)
      })
      return
    }
    const route = buildSlashRoute(def.cmd, arg)
    if (route) {
      navigate(route)
      close()
    }
  }

  function runUrlHintAction() {
    const hint = urlHint.data
    if (!hint) return

    if (hint.kind === 'jira') {
      const key = String(hint.extracted.key ?? '')
      void callTool('track_jira', { issue: key })
        .catch(() => undefined)
        .finally(() => {
          navigate(`/jira?q=${encodeURIComponent(key)}`)
        })
      close()
      return
    }

    if (hint.kind === 'webex') {
      const spaceUrl = String(hint.extracted.url ?? query)
      window.open(spaceUrl, '_blank', 'noopener,noreferrer')
      close()
      return
    }

    const value =
      hint.kind === 'github'
        ? `${String(hint.extracted.repo ?? '')}#${String(hint.extracted.pr_number ?? '')}`
        : hint.kind === 'file'
          ? String(hint.extracted.path ?? query)
          : query
    setAttachRef({ kind: hint.kind, value, url: query })
    close()
  }

  const slashHint = 'Type / for commands · paste a URL to log · Esc to close'

  const body = (
    <div
      onKeyDown={(event) => {
        if (isSlash) {
          if (event.key === 'ArrowDown') {
            event.preventDefault()
            setActiveIndex((index) => Math.min(slashMatches.length - 1, index + 1))
          } else if (event.key === 'ArrowUp') {
            event.preventDefault()
            setActiveIndex((index) => Math.max(0, index - 1))
          } else if (event.key === 'Enter' && slashMatches[activeIndex]) {
            event.preventDefault()
            const { arg } = parseSlashInput(query)
            runSlashCommand(slashMatches[activeIndex], arg)
          }
          return
        }
        if (isUrl) {
          if (event.key === 'Enter' && urlHint.data) {
            event.preventDefault()
            runUrlHintAction()
          }
          return
        }
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
          placeholder="Search ledger, todos, JIRAs, Webex, skills, and reports (or type / for commands)"
          className="w-full bg-transparent text-14 text-text-primary outline-none placeholder:text-text-muted"
        />
      </div>

      {isSlash && slashMatches.length === 0 && query.trim() === '/' && (
        <div className="border-b border-border-subtle px-4 py-2 text-12 text-text-muted">{slashHint}</div>
      )}

      <div className="max-h-[70vh] overflow-y-auto p-3">
          {isSlash ? (
            (slashMatches.length === 0 && query.trim() !== '/') ? (
              <PaletteHint text="No matching commands." />
            ) : (
              <section className="mb-4">
                <div className="px-2 py-1 text-12 uppercase tracking-[0.18em] text-text-muted">Commands</div>
                <div className="mt-1 space-y-1">
                {(query.trim() === '/' ? slashMatches.length > 0 ? slashMatches : matchSlashCommands('/'): slashMatches).map((def, index) => (
                  <button
                    key={def.cmd}
                    type="button"
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => runSlashCommand(def, parseSlashInput(query).arg)}
                    className={`flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left transition-colors duration-fast ease-out ${
                      index === activeIndex ? 'bg-bg-elevated' : 'hover:bg-bg-elevated/70'
                    }`}
                  >
                    <span className="mt-0.5 text-text-muted">
                      <Terminal size={15} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-13 text-text-primary">{def.cmd}</span>
                      <span className="mt-0.5 block truncate text-12 text-text-muted">{def.label}</span>
                    </span>
                  </button>
                ))}
              </div>
              </section>
            )
          ) : isUrl ? (
          <section className="mb-4">
            <div className="px-2 py-1 text-12 uppercase tracking-[0.18em] text-text-muted">Paste detected</div>
            {urlHint.isLoading ? (
              <div className="px-3 py-6 text-center text-13 text-text-muted">Classifying…</div>
            ) : urlHint.data ? (
              <button
                type="button"
                onClick={() => runUrlHintAction()}
                className="flex w-full items-start gap-3 rounded-lg bg-bg-elevated px-3 py-2 text-left transition-colors duration-fast ease-out hover:bg-bg-elevated/70"
              >
                <span className="mt-0.5 text-text-muted">
                  <Link2 size={15} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-13 text-text-primary">{urlHintActionLabel(urlHint.data)}</span>
                  <span className="mt-0.5 block truncate text-12 text-text-muted">{urlHint.data.kind}</span>
                </span>
              </button>
            ) : (
              <PaletteHint text="Could not classify this URL." />
            )}
          </section>
        ) : (
          <>
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
              <PaletteHint text="Type / for commands · paste a URL to log · Esc to close" />
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
          </>
        )}
      </div>
    </div>
  )

  const briefDialog = (
    <Dialog open={briefOpen} onOpenChange={setBriefOpen}>
      <DialogContent>
        <DialogTitle>Today's brief</DialogTitle>
        <div className="mt-4 max-h-[60vh] overflow-y-auto whitespace-pre-wrap text-13 leading-6 text-text-secondary">
          {briefPending ? 'Running…' : briefMarkdown || 'No brief available.'}
        </div>
      </DialogContent>
    </Dialog>
  )

  const attachDialog = attachRef && (
    <AttachRefDialog
      open={Boolean(attachRef)}
      onOpenChange={(next) => {
        if (!next) setAttachRef(null)
      }}
      ref={attachRef}
    />
  )

  if (!open && typeof document === 'undefined') return null

  if (typeof document === 'undefined') {
    return <div className="rounded-xl border border-border-strong bg-bg-panel shadow-md">{body}</div>
  }

  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="top-[14vh] max-w-2xl translate-y-0 p-0">
          {body}
        </DialogContent>
      </Dialog>
      {briefDialog}
      {attachDialog}
    </>
  )
}
