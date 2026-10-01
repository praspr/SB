import { callTool } from './mcp'

export const ATTENTION_QUERY_KEY = ['triage', 'attention'] as const

export type WebexHandledAction = 'completed' | 'ignored'

export type WebexHandledResult = {
  ok: true
  message_id: string
  action: WebexHandledAction
}

export type WebexUnhandledResult = {
  ok: true
  message_id: string
}

export function markHandled(messageId: string, action: WebexHandledAction = 'completed'): Promise<WebexHandledResult> {
  return callTool<WebexHandledResult>('webex_mark_handled', { message_id: messageId, action })
}

export function markUnhandled(messageId: string): Promise<WebexUnhandledResult> {
  return callTool<WebexUnhandledResult>('webex_mark_unhandled', { message_id: messageId })
}
