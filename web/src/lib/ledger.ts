import { callTool } from './mcp'

export type LedgerRef = {
  kind: string
  value: string
  url?: string
  label?: string
  [key: string]: unknown
}

export type LedgerEntry = {
  id: number
  ts: string
  session_id: string
  project: string
  scope?: string | null
  action_verb: string
  summary: string
  body?: string | null
  refs: LedgerRef[]
  source_harness: string
  agent_model?: string | null
  working_dir?: string | null
  origin: string
  redaction_applied: boolean
  redaction_rules_version?: number
  created_at?: string
  open_status?: string
  open_refs?: LedgerRef[]
}

export type LedgerLogInput = {
  summary: string
  project: string
  action_verb?: string
  body?: string
  scope?: string
  refs?: LedgerRef[]
  session_id?: string
  agent?: string
  working_dir?: string
  source_harness?: string
}

export type LedgerLogResult = {
  id: number
  ts: string
  redaction_applied: boolean
  was_new: boolean
  session_id?: string
  persisted_to_file?: boolean
}

export type LedgerBatchLogResult = {
  results: Array<LedgerLogResult | { error: string; entry: LedgerLogInput }>
}

export type LedgerSearchFilters = {
  q?: string
  project?: string
  since?: string
  until?: string
  verb?: string
  session_id?: string
  limit?: number
}

export type LedgerContext = {
  entries: LedgerEntry[]
  open_threads: LedgerEntry[]
  tracked_refs: LedgerRef[]
}

export type LedgerProject = {
  project: string
  root_path: string
  changelog_path: string
  sync_mode: 'dual' | 'sqlite-only' | string
  added_at?: string
}

export type RegisterLedgerProjectInput = {
  project: string
  root_path: string
  changelog_path?: string
  sync_mode?: 'dual' | 'sqlite-only'
}

export type LedgerSyncResult = {
  project_count?: number
  scanned_count?: number
  imported_count?: number
  skipped_count?: number
  errors?: string[]
  [key: string]: unknown
}

export function ledgerLog(input: LedgerLogInput): Promise<LedgerLogResult> {
  return callTool<LedgerLogResult>('ledger_log', input)
}

export function ledgerBatchLog(entries: LedgerLogInput[]): Promise<LedgerBatchLogResult> {
  return callTool<LedgerBatchLogResult>('ledger_batch_log', { entries })
}

export function ledgerSearch(filters: LedgerSearchFilters = {}): Promise<LedgerEntry[]> {
  return callTool<LedgerEntry[]>('ledger_search', filters)
}

export function ledgerContext(project: string, since?: string, limit?: number): Promise<LedgerContext> {
  return callTool<LedgerContext>('ledger_context', {
    project,
    ...(since ? { since } : {}),
    ...(typeof limit === 'number' ? { limit } : {}),
  })
}

export function ledgerByRef(kind: string, value: string, limit?: number): Promise<LedgerEntry[]> {
  return callTool<LedgerEntry[]>('ledger_by_ref', {
    kind,
    value,
    ...(typeof limit === 'number' ? { limit } : {}),
  })
}

export function ledgerOpenThreads(project?: string): Promise<LedgerEntry[]> {
  return callTool<LedgerEntry[]>('ledger_open_threads', project ? { project } : {})
}

export function ledgerProjects(): Promise<LedgerProject[]> {
  return callTool<LedgerProject[]>('ledger_projects')
}

export function ledgerRegisterProject(input: RegisterLedgerProjectInput): Promise<LedgerProject> {
  return callTool<LedgerProject>('ledger_register_project', input)
}

export function syncLedgerFromFiles(): Promise<LedgerSyncResult> {
  return callTool<LedgerSyncResult>('sync_ledger_from_files')
}
