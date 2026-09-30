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

export type WebexSpaceOption = {
  id: string
  name: string
}

type RawSpace = {
  id: string
  name: string
}

export async function listWebexSpaces(): Promise<WebexSpaceOption[]> {
  const rows = await callTool<RawSpace[]>('list_webex_spaces')
  return rows.map((row) => ({ id: row.id, name: row.name }))
}
