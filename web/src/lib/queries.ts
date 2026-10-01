import { QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  type JiraPriority,
  type JiraStatus,
  type JiraTicket,
  type Meeting,
  type Task,
  type WebexMessage,
  type WebexSpace,
} from './mock-data'
import { callTool } from './mcp'

export const TASKS_QUERY_KEY = ['tasks'] as const

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

// ---- Tasks (real data via the unified sb MCP) ----

type SbTodo = {
  id: number
  title: string
  description: string
  priority: number
  due_date: string | null
  due_time: string | null
  remind_before_minutes: number | null
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
    remind_before_minutes: t.remind_before_minutes,
    is_completed: t.is_completed,
    domain,
    source: src,
    ref: t.external_ref ?? undefined,
  }
}

export async function fetchTasks(): Promise<Task[]> {
  const raw = await callTool<SbTodo[]>('todo_list', { status: 'all' })
  return raw.map(todoToTask)
}

export function markTaskCompleted(tasks: Task[] | undefined, taskId: number): Task[] | undefined {
  return tasks?.map((task) => (task.id === taskId ? { ...task, is_completed: true } : task))
}

export function reopenTask(tasks: Task[] | undefined, taskId: number): Task[] | undefined {
  return tasks?.map((task) => (task.id === taskId ? { ...task, is_completed: false } : task))
}

export type TaskUpdateInput = {
  title?: string
  description?: string
  priority?: Task['priority']
  due_date?: string | null
  due_time?: string | null
  remind_before_minutes?: number | null
  domain?: Task['domain']
  goal_id?: number | null
  jira_ref?: string | null
  recurrence_rule?: string | null
  parent_todo_id?: number | null
}

export function restoreSnapshots<T>(
  queryClient: QueryClient,
  previous: Array<[readonly unknown[], T | undefined]> | undefined,
): void {
  previous?.forEach(([key, data]) => {
    queryClient.setQueryData(key, data)
  })
}

export async function createTask(input: {
  title: string
  priority: Task['priority']
  domain: Task['domain']
}): Promise<Task> {
  const raw = await callTool<SbTodo>('todo_add', {
    title: input.title,
    priority: input.priority,
    domain: input.domain,
  })
  return todoToTask(raw)
}

export async function updateTask(taskId: number, patch: TaskUpdateInput): Promise<Task> {
  const payload = Object.fromEntries(
    Object.entries({ todo_id: taskId, ...patch }).filter(([, value]) => value !== undefined),
  )
  const raw = await callTool<SbTodo>('todo_update', payload)
  return todoToTask(raw)
}

export async function uncompleteTask(taskId: number): Promise<number> {
  await callTool<SbTodo>('todo_uncomplete', { todo_id: taskId })
  return taskId
}

export function useTasks() {
  return useQuery({ queryKey: TASKS_QUERY_KEY, queryFn: fetchTasks, retry: 1 })
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
      await callTool<SbTodo>('todo_complete', { todo_id: taskId })
      return taskId
    },
    onMutate: async (taskId: number) => {
      await queryClient.cancelQueries({ queryKey: TASKS_QUERY_KEY })
      const previous = queryClient.getQueriesData<Task[]>({ queryKey: TASKS_QUERY_KEY })
      queryClient.setQueriesData<Task[]>({ queryKey: TASKS_QUERY_KEY }, (old) =>
        markTaskCompleted(old, taskId)
      )
      return { previous }
    },
    onError: (_err, _taskId, context) => {
      restoreSnapshots(queryClient, context?.previous)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
    },
  })
}

export function useUncompleteTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uncompleteTask,
    onMutate: async (taskId: number) => {
      await queryClient.cancelQueries({ queryKey: TASKS_QUERY_KEY })
      const previous = queryClient.getQueriesData<Task[]>({ queryKey: TASKS_QUERY_KEY })
      queryClient.setQueriesData<Task[]>({ queryKey: TASKS_QUERY_KEY }, (old) =>
        reopenTask(old, taskId),
      )
      return { previous }
    },
    onError: (_err, _taskId, context) => {
      restoreSnapshots(queryClient, context?.previous)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
    },
  })
}

export function useUpdateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ taskId, patch }: { taskId: number; patch: TaskUpdateInput }) => updateTask(taskId, patch),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
    },
  })
}

export function useAddTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createTask,
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
    },
  })
}

// ---- Meetings (read-only Webex mirror) ----

type RawMeeting = {
  id: string
  title: string
  start: string
  end: string
  join_url?: string | null
  attendees?: { name?: string; email?: string }[]
  agenda?: string | null
}

export function toMeeting(row: RawMeeting): Meeting {
  return {
    id: row.id,
    title: row.title,
    start: row.start,
    end: row.end,
    join_url: row.join_url || undefined,
    attendees: (row.attendees ?? []).map((person) => ({
      name: person.name || person.email || 'Guest',
      email: person.email || person.name || '',
    })),
    is_organizer: false,
    agenda: row.agenda || undefined,
  }
}

export async function listMeetings(): Promise<Meeting[]> {
  const rows = await callTool<RawMeeting[]>('list_webex_meetings')
  return rows.map(toMeeting)
}

export function useMeetings() {
  return useQuery({ queryKey: ['meetings'], queryFn: listMeetings })
}

export function useTodayMeetings() {
  return useQuery({
    queryKey: ['meetings', 'today'],
    queryFn: async () => {
      const meetings = await listMeetings()
      return meetings
        .filter((m) => isToday(m.start))
        .sort((a, b) => a.start.localeCompare(b.start))
    },
  })
}

// ---- Webex ----

type RawMessage = {
  id: string
  space_id: string
  space_name: string
  sender_name: string
  sender_email?: string | null
  is_dm: boolean | number
  is_mention: boolean | number
  is_unread: boolean | number
  preview: string
  occurred_at: string
  deep_link?: string | null
}

type RawSpace = {
  id: string
  name: string
  is_dm: boolean | number
  unread_count: number
  last_activity?: string | null
  members_count: number
}

export function toWebexMessage(row: RawMessage): WebexMessage {
  return {
    id: row.id,
    from: { name: row.sender_name, email: row.sender_email || '' },
    space: row.space_name,
    space_id: row.space_id,
    is_dm: Boolean(row.is_dm),
    is_mention: Boolean(row.is_mention),
    is_unread: Boolean(row.is_unread),
    preview: row.preview,
    ts: row.occurred_at,
    url: row.deep_link || undefined,
  }
}

export function toWebexSpace(row: RawSpace): WebexSpace {
  return {
    id: row.id,
    name: row.name,
    is_dm: Boolean(row.is_dm),
    unread_count: row.unread_count,
    last_activity: row.last_activity || '',
    members_count: row.members_count,
  }
}

export function useWebexMessages() {
  return useQuery({
    queryKey: ['webex', 'messages'],
    queryFn: async () => {
      const rows = await callTool<RawMessage[]>('list_webex_messages')
      return rows.map(toWebexMessage)
    },
  })
}

export function useWebexSpaces() {
  return useQuery({
    queryKey: ['webex', 'spaces'],
    queryFn: async () => {
      const rows = await callTool<RawSpace[]>('list_webex_spaces')
      return rows.map(toWebexSpace)
    },
  })
}

export type WebexServiceStatus = {
  authenticated: boolean
  meetings_count: number
  messages_count: number
  login_path: string
}

export function useWebexStatus() {
  return useQuery({
    queryKey: ['webex', 'status'],
    queryFn: () => callTool<WebexServiceStatus>('webex_status'),
    staleTime: 30_000,
    retry: 1,
  })
}

export function useWebexAttention() {
  return useQuery({
    queryKey: ['webex', 'attention'],
    queryFn: async () => {
      const rows = await callTool<RawMessage[]>('webex_attention', { limit: 20 })
      return rows.map(toWebexMessage)
    },
  })
}

export type WebexSyncResult = {
  meetings: number
  spaces: number
  messages: number
  errors: string[]
}

export function useSyncWebex() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => callTool<WebexSyncResult>('sync_webex'),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['webex'] })
      queryClient.invalidateQueries({ queryKey: ['meetings'] })
    },
  })
}

export type WebexSummary = {
  summary: string
  citations: string[]
  mode: string
}

export function summarizeWebexSpace(spaceId: string): Promise<WebexSummary> {
  return callTool<WebexSummary>('summarize_webex_space', { space_id: spaceId })
}

// ---- JIRA (pull-only tools on the unified sb MCP) ----

export async function listJiraTickets(filters?: {
  status?: JiraStatus | 'all' | 'active'
  priority?: JiraPriority | 'all'
  project?: string | 'all'
  projects?: string[]
  q?: string
  limit?: number
}): Promise<JiraTicket[]> {
  const specificStatus = filters?.status && filters.status !== 'all' && filters.status !== 'active'
  return callTool<JiraTicket[]>('list_jira_tickets', {
    ...(specificStatus ? { status: filters.status } : {}),
    ...(filters?.status === 'active' ? { hide_closed: true } : {}),
    ...(filters?.priority && filters.priority !== 'all' ? { priority: filters.priority } : {}),
    ...(filters?.project && filters.project !== 'all' ? { project: filters.project } : {}),
    ...(filters?.projects ? { projects: filters.projects } : {}),
    ...(filters?.q ? { q: filters.q } : {}),
    ...(filters?.limit ? { limit: filters.limit } : {}),
  })
}

export function useJiraTickets(filters?: {
  status?: JiraStatus | 'all' | 'active'
  priority?: JiraPriority | 'all'
  project?: string | 'all'
  projects?: string[]
  q?: string
  limit?: number
}) {
  return useQuery({
    queryKey: ['jira', 'tickets', filters],
    queryFn: () => listJiraTickets(filters),
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

export function syncJira(): Promise<JiraSyncResult> {
  return callTool<JiraSyncResult>('sync_jira')
}

export function useSyncJira() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: syncJira,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jira'] })
    },
  })
}

export type TrackJiraResult = {
  key: string | null
  tracked: boolean
  errors: string[]
}

export function trackJira(issue: string): Promise<TrackJiraResult> {
  return callTool<TrackJiraResult>('track_jira', { issue })
}

export function useTrackJira() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: trackJira,
    onSuccess: (result) => {
      if (result.tracked) queryClient.invalidateQueries({ queryKey: ['jira'] })
    },
  })
}

export function untrackJira(key: string): Promise<TrackJiraResult> {
  return callTool<TrackJiraResult>('untrack_jira', { key })
}

export function useUntrackJira() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: untrackJira,
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
  tracked_count?: number
}

export function fetchJiraStatus(): Promise<JiraServiceStatus> {
  return callTool<JiraServiceStatus>('jira_status')
}

export function useJiraStatus() {
  return useQuery({
    queryKey: ['jira', 'status'],
    queryFn: fetchJiraStatus,
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
