import { callTool } from './mcp'

export type SignalRecord = {
  id: number
  source: string
  kind: string
  occurred_at: string
  title: string
  body?: string | null
}

export type AdapterState = {
  adapter: string
  last_run_at: string
  signal_count: number
  error: string | null
}

export function searchSignals(filters?: { query?: string; source?: string }): Promise<SignalRecord[]> {
  return callTool<SignalRecord[]>('search_signals', {
    ...(filters?.query ? { q: filters.query } : {}),
    ...(filters?.source ? { source: filters.source } : {}),
  })
}

export function syncAdapters(): Promise<{ adapters: Record<string, { signal_count: number; error: string | null }> }> {
  return callTool('sync_adapters')
}

export function syncStatus(): Promise<{ states: AdapterState[] }> {
  return callTool('sync_status')
}

export function cite(signal: SignalRecord): string {
  return `[signal:${signal.id}] ${signal.title}`
}
