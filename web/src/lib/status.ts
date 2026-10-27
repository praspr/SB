import { callTool } from './mcp'

export type CoreStatus = {
  status: 'ok' | 'degraded' | string
  version: string
  database: {
    ready: boolean
    schema_version: number | null
    path?: string
  }
  disk?: {
    total: number
    used: number
    free: number
    percent: number
  } | null
  counts: {
    tools: number
    prompts: number
    resources: number
  }
}

export type StatusPhase = 'connected' | 'degraded'

export function statusPhase(
  data: CoreStatus | undefined,
  failed: boolean,
): StatusPhase {
  if (failed || !data || data.status !== 'ok' || !data.database.ready) return 'degraded'
  return 'connected'
}

export function fetchCoreStatus(): Promise<CoreStatus> {
  return callTool<CoreStatus>('system_status')
}
