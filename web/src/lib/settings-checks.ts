import { callTool } from '@/lib/mcp'
import { fetchCoreStatus } from '@/lib/status'

export type CheckResult = {
  name: string
  status: 'ok' | 'fail' | 'loading' | 'unknown'
  label: string
  subtext?: string
  error?: string
}

type CheckDefinition = {
  id: string
  label: string
  fn: () => Promise<CheckResult>
}

const CORE_HEALTH_URL = '/health'
const CLAUDEGATE_URL = 'http://localhost:9999/'
const CURSOR_SESSION_PATH = '/proxy/cursor/api/usage-summary'

function messageFromError(error: unknown): string {
  if (error instanceof Error && error.message) return error.message
  return 'Unknown error'
}

function ok(name: string, label: string, subtext?: string): CheckResult {
  return { name, label, status: 'ok', subtext }
}

function fail(name: string, label: string, error: unknown, subtext?: string): CheckResult {
  const message = messageFromError(error)
  return {
    name,
    label,
    status: 'fail',
    subtext: subtext ?? message,
    error: message,
  }
}

function unknown(name: string, label: string, subtext: string): CheckResult {
  return { name, label, status: 'unknown', subtext }
}

function readBooleanField(data: unknown, keys: string[]): boolean | undefined {
  if (!data || typeof data !== 'object') return undefined

  for (const key of keys) {
    const value = (data as Record<string, unknown>)[key]
    if (typeof value === 'boolean') return value
    if (typeof value === 'string' && key === 'status') {
      if (value === 'ok' || value === 'connected' || value === 'ready') return true
      if (value === 'error' || value === 'fail' || value === 'disconnected') return false
    }
  }

  for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
    if (!/(status|reachable|signed|auth|connected|ready|ok)/i.test(key)) continue
    if (typeof value === 'boolean') return value
    if (typeof value === 'string') return value.length > 0 && value !== 'false' && value !== 'error'
    if (typeof value === 'number') return value > 0
  }

  return undefined
}

function readNumberField(data: unknown, keys: string[]): number | undefined {
  if (!data || typeof data !== 'object') return undefined
  for (const key of keys) {
    const value = (data as Record<string, unknown>)[key]
    if (typeof value === 'number') return value
  }
  return undefined
}

export async function checkHealth(): Promise<CheckResult> {
  const name = 'health'
  const label = 'sb-core MCP'

  try {
    const response = await fetch(CORE_HEALTH_URL, { signal: AbortSignal.timeout(1500) })
    if (!response.ok) return fail(name, label, new Error(`HTTP ${response.status}`), `HTTP ${response.status}`)
    return ok(name, label, CORE_HEALTH_URL)
  } catch (error) {
    return fail(name, label, error)
  }
}

export async function checkCoreDb(): Promise<CheckResult> {
  const name = 'core-db'
  const label = 'Core database'

  try {
    const data = await fetchCoreStatus()
    const subtext = data.database.schema_version != null
      ? `schema v${data.database.schema_version}`
      : 'schema unavailable'

    if (data.database.ready) return ok(name, label, subtext)
    return {
      name,
      label,
      status: 'fail',
      subtext,
      error: 'Database not ready',
    }
  } catch (error) {
    return fail(name, label, error)
  }
}

export async function checkJira(): Promise<CheckResult> {
  const name = 'jira'
  const label = 'Atlassian JIRA'

  try {
    const data = await callTool<unknown>('jira_status')
    const reachable = readBooleanField(data, ['reachable', 'atlassian_reachable', 'status', 'connected'])
    const ticketCount = readNumberField(data, ['ticket_count', 'tickets_count'])
    const subtext = typeof ticketCount === 'number' ? `${ticketCount} tickets` : undefined

    if (reachable) return ok(name, label, subtext)
    return {
      name,
      label,
      status: 'fail',
      subtext,
      error: 'JIRA is not reachable',
    }
  } catch (error) {
    return fail(name, label, error)
  }
}

export async function checkWebex(): Promise<CheckResult> {
  const name = 'webex'
  const label = 'Webex'

  try {
    const data = await callTool<unknown>('webex_status')
    const signedIn = readBooleanField(data, ['signed_in', 'authenticated', 'status'])
    const subtext = signedIn ? 'signed in' : 'not signed in'

    if (signedIn) return ok(name, label, subtext)
    return {
      name,
      label,
      status: 'fail',
      subtext,
      error: 'Webex is not signed in',
    }
  } catch (error) {
    return fail(name, label, error)
  }
}

export async function checkClaudegate(): Promise<CheckResult> {
  const name = 'claudegate'
  const label = 'Copilot proxy'

  try {
    await fetch(CLAUDEGATE_URL, {
      method: 'HEAD',
      mode: 'no-cors',
      signal: AbortSignal.timeout(1500),
    })
    return ok(name, label, CLAUDEGATE_URL)
  } catch (error) {
    return fail(name, label, error, CLAUDEGATE_URL)
  }
}

export async function checkCursorSession(): Promise<CheckResult> {
  const name = 'cursor'
  const label = 'Cursor session'

  if (!CURSOR_SESSION_PATH) return unknown(name, label, 'probe unavailable')

  try {
    const response = await fetch(CURSOR_SESSION_PATH, { signal: AbortSignal.timeout(1500) })
    if (!response.ok) return fail(name, label, new Error(`HTTP ${response.status}`), `HTTP ${response.status}`)
    return ok(name, label, CURSOR_SESSION_PATH)
  } catch (error) {
    return fail(name, label, error)
  }
}

export const SETTING_CHECKS: CheckDefinition[] = [
  { id: 'health', label: 'sb-core MCP', fn: checkHealth },
  { id: 'core-db', label: 'Core database', fn: checkCoreDb },
  { id: 'jira', label: 'Atlassian JIRA', fn: checkJira },
  { id: 'webex', label: 'Webex', fn: checkWebex },
  { id: 'claudegate', label: 'Copilot proxy', fn: checkClaudegate },
  { id: 'cursor', label: 'Cursor session', fn: checkCursorSession },
]
