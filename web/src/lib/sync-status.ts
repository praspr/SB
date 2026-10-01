import { callTool } from './mcp'

export type SyncAdapterState = {
  adapter: string
  last_run_at: string
  signal_count: number
  error: string | null
}

export type SyncStatusResult = {
  states: SyncAdapterState[]
}

export function syncStatus(): Promise<SyncStatusResult> {
  return callTool<SyncStatusResult>('sync_status')
}
