import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  mockJiraTickets,
  mockMeetings,
  mockTasks,
  mockWebexMessages,
  mockWebexSpaces,
  type JiraPriority,
  type JiraStatus,
  type JiraTicket,
  type Task,
} from './mock-data'

const DELAY = 200

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), DELAY))
}

function isToday(iso?: string): boolean {
  if (!iso) return false
  const d = new Date(iso)
  const now = new Date()
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  )
}

// ---- Tasks (real data via sb-todos service :8788 proxied at /proxy/todos) ----

type SbTodo = {
  id: number
  title: string
  description: string
  priority: number
  due_date: string | null
  due_time: string | null
  is_completed: boolean
  completed_at: string | null
  tags: string[]
  external_source: string | null
  external_ref: string | null
  domain: string
  created_at: string
  updated_at: string
}

function todoToTask(t: SbTodo): Task {
  const src: Task['source'] =
    t.external_source === 'jira' ? 'jira' : t.external_source === 'changelog' ? 'changelog' : 'manual'
  const domain: Task['domain'] =
    t.domain === 'work' || t.domain === 'learning' || t.domain === 'personal' ? t.domain : 'work'
  const priority = (Math.min(4, Math.max(1, t.priority)) as Task['priority'])
  return {
    id: t.id,
    title: t.title,
    description: t.description || undefined,
    priority,
    due_date: t.due_date ?? undefined,
    due_time: t.due_time ?? undefined,
    is_completed: t.is_completed,
    domain,
    source: src,
    ref: t.external_ref ?? undefined,
  }
}

async function fetchTasks(): Promise<Task[]> {
  const res = await fetch('/proxy/todos/api/todos?status=all')
  if (!res.ok) throw new Error(`sb-todos ${res.status}`)
  const raw: SbTodo[] = await res.json()
  return raw.map(todoToTask)
}

export function useTasks() {
  return useQuery({ queryKey: ['tasks'], queryFn: fetchTasks, retry: 1 })
}

export function useTodayTasks() {
  return useQuery({
    queryKey: ['tasks', 'today'],
    queryFn: async () => {
      const tasks = await fetchTasks()
      return tasks
        .filter((t) => !t.is_completed)
        .sort((a, b) => {
          if (a.priority !== b.priority) return a.priority - b.priority
          const aDue = a.due_date ?? '9999-99-99'
          const bDue = b.due_date ?? '9999-99-99'
          return aDue.localeCompare(bDue)
        })
        .slice(0, 7)
    },
    retry: 1,
  })
}

export function useCompleteTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (taskId: number) => {
      const res = await fetch(`/proxy/todos/api/todos/${taskId}/complete`, { method: 'POST' })
      if (!res.ok) throw new Error(`sb-todos complete ${res.status}`)
      return taskId
    },
    onMutate: async (taskId: number) => {
      await queryClient.cancelQueries({ queryKey: ['tasks'] })
      const previous = queryClient.getQueriesData<Task[]>({ queryKey: ['tasks'] })
      queryClient.setQueriesData<Task[]>({ queryKey: ['tasks'] }, (old) =>
        old?.map((t) => (t.id === taskId ? { ...t, is_completed: true } : t))
      )
      return { previous }
    },
    onError: (_err, _taskId, context) => {
      context?.previous.forEach(([key, data]) => {
        queryClient.setQueryData(key, data)
      })
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function useAddTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: { title: string; priority: Task['priority']; domain: Task['domain'] }) => {
      const res = await fetch('/proxy/todos/api/todos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: input.title,
          priority: input.priority,
          domain: input.domain,
        }),
      })
      if (!res.ok) throw new Error(`sb-todos add ${res.status}`)
      const raw: SbTodo = await res.json()
      return todoToTask(raw)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

// ---- Meetings ----

async function fetchMeetings() {
  return delay(mockMeetings)
}

export function useMeetings() {
  return useQuery({ queryKey: ['meetings'], queryFn: fetchMeetings })
}

export function useTodayMeetings() {
  return useQuery({
    queryKey: ['meetings', 'today'],
    queryFn: async () => {
      const meetings = await fetchMeetings()
      return meetings
        .filter((m) => isToday(m.start))
        .sort((a, b) => a.start.localeCompare(b.start))
    },
  })
}

// ---- Webex ----

async function fetchWebexMessages() {
  return delay(mockWebexMessages)
}

async function fetchWebexSpaces() {
  return delay(mockWebexSpaces)
}

export function useWebexMessages() {
  return useQuery({ queryKey: ['webex', 'messages'], queryFn: fetchWebexMessages })
}

export function useWebexSpaces() {
  return useQuery({ queryKey: ['webex', 'spaces'], queryFn: fetchWebexSpaces })
}

// ---- JIRA (real data via sb-jira service :8789 proxied at /proxy/jira) ----

export function useJiraTickets(filters?: {
  status?: JiraStatus | 'all'
  priority?: JiraPriority | 'all'
  project?: string | 'all'
  q?: string
}) {
  return useQuery({
    queryKey: ['jira', 'tickets', filters],
    queryFn: async (): Promise<JiraTicket[]> => {
      const res = await fetch('/proxy/jira/api/jira/tickets')
      if (!res.ok) throw new Error(`sb-jira ${res.status}`)
      const all: JiraTicket[] = await res.json()
      return all.filter((t) => {
        if (filters?.status && filters.status !== 'all' && t.status !== filters.status) return false
        if (filters?.priority && filters.priority !== 'all' && t.priority !== filters.priority) return false
        if (filters?.project && filters.project !== 'all' && t.project !== filters.project) return false
        if (filters?.q && !`${t.key} ${t.title}`.toLowerCase().includes(filters.q.toLowerCase())) return false
        return true
      })
    },
    staleTime: 30_000,
    retry: 1,
  })
}

export type JiraSyncResult = {
  updated_count: number
  added_count: number
  unchanged_count: number
  errors: string[]
  duration_ms: number
  history_row_appended: boolean
}

export function useSyncJira() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (): Promise<JiraSyncResult> => {
      const res = await fetch('/proxy/jira/api/jira/sync', { method: 'POST' })
      if (!res.ok) throw new Error(`sb-jira sync ${res.status}`)
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jira'] })
    },
  })
}

export type JiraServiceStatus = {
  last_sync_at: string | null
  atlassian_reachable: boolean
  atlassian_error: string | null
  tickets_count: number
}

export function useJiraStatus() {
  return useQuery({
    queryKey: ['jira', 'status'],
    queryFn: async (): Promise<JiraServiceStatus> => {
      const res = await fetch('/proxy/jira/api/jira/status')
      if (!res.ok) throw new Error(`sb-jira status ${res.status}`)
      return res.json()
    },
    staleTime: 60_000,
    retry: 1,
  })
}

// ---- Claudegate usage (real data, proxied) ----

export type ClaudegateStatus = {
  copilot: {
    plan: string
    premium: {
      used: number
      total: number
      remaining: number
      percent_used: number
      unlimited: boolean
      overage_permitted: boolean
    }
    chat: { unlimited: boolean }
    completions: { unlimited: boolean }
    reset_date: string // YYYY-MM-DD
    cached_at: string
    stale: boolean
  }
}

export function useClaudegateUsage() {
  return useQuery({
    queryKey: ['claudegate', 'usage'],
    queryFn: async (): Promise<ClaudegateStatus['copilot']> => {
      const res = await fetch('/proxy/claudegate/api/status')
      if (!res.ok) throw new Error(`claudegate ${res.status}`)
      const data = await res.json()
      return data.copilot
    },
    refetchInterval: 60_000, // refresh every 60s
    staleTime: 30_000,
    retry: 1,
  })
}

// ---- Cursor usage (real data, proxied with server-side cookie injection) ----

export type CursorUsageRaw = Record<string, unknown>

export type CursorUsage = {
  raw: CursorUsageRaw
  membershipType: string | null
  primaryUsed: number | null
  primaryTotal: number | null
  primaryPercent: number | null
  primaryLabel: string // e.g. "Premium requests" or "Fast requests"
  resetDate: string | null // if present
}

function readNumberPath(obj: unknown, pathParts: string[]): number | null {
  let cur: any = obj
  for (const part of pathParts) {
    if (cur == null || typeof cur !== 'object') return null
    cur = cur[part]
  }
  return typeof cur === 'number' ? cur : null
}

function normaliseCursorUsage(raw: any): CursorUsage {
  // Try several known shapes, in priority order:
  //   raw.individualUsage.overall.{used, limit}   (current Cursor API, Sep 2026)
  //   raw.premiumRequests.{numRequests, maxRequestUsage}
  //   raw.gpt4.{numRequests, maxRequestUsage}
  //   raw.fastPremiumRequests.{used, limit}
  const candidates: Array<{ path: string[]; usedKey: string; totalKey: string; label: string }> = [
    { path: ['individualUsage', 'overall'], usedKey: 'used', totalKey: 'limit', label: 'Premium requests' },
    { path: ['premiumRequests'], usedKey: 'numRequests', totalKey: 'maxRequestUsage', label: 'Premium requests' },
    { path: ['gpt4'], usedKey: 'numRequests', totalKey: 'maxRequestUsage', label: 'GPT-4 requests' },
    { path: ['fastPremiumRequests'], usedKey: 'used', totalKey: 'limit', label: 'Fast requests' },
  ]

  let used: number | null = null
  let total: number | null = null
  let label = 'Requests'

  for (const c of candidates) {
    const u = readNumberPath(raw, [...c.path, c.usedKey])
    const t = readNumberPath(raw, [...c.path, c.totalKey])
    if (u != null && t != null) {
      used = u
      total = t
      label = c.label
      break
    }
  }

  const percent = used != null && total != null && total > 0 ? (used / total) * 100 : null

  return {
    raw,
    membershipType: raw?.membershipType ?? raw?.plan ?? null,
    primaryUsed: used,
    primaryTotal: total,
    primaryPercent: percent,
    primaryLabel: label,
    resetDate: raw?.billingCycleEnd ?? raw?.resetDate ?? raw?.periodEnd ?? null,
  }
}

export function useCursorUsage() {
  return useQuery({
    queryKey: ['cursor', 'usage'],
    queryFn: async (): Promise<CursorUsage> => {
      const res = await fetch('/proxy/cursor/api/usage-summary')
      if (res.status === 401 || res.status === 403) throw new Error('cursor: not signed in')
      if (!res.ok) throw new Error(`cursor ${res.status}`)
      const raw = await res.json()
      return normaliseCursorUsage(raw)
    },
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: 1,
  })
}
