import { callTool } from './mcp'

export type WebexPostResult = {
  posted: boolean
  space_id: string
  message_type: string
  result?: unknown
  error?: string
}

export function webexPostMessage(space_id: string, markdown: string, message_type = 'text'): Promise<WebexPostResult> {
  return callTool<WebexPostResult>('webex_post_message', { space_id, markdown, message_type })
}
