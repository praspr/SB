import { callTool } from './mcp'

export type WebexMutedSpace = {
  id: string
  name?: string
  muted: boolean
  found?: boolean
  unread_count?: number
  last_activity?: string | null
}

export function muteSpace(space_id: string): Promise<WebexMutedSpace> {
  return callTool<WebexMutedSpace>('mute_space', { space_id })
}

export function unmuteSpace(space_id: string): Promise<WebexMutedSpace> {
  return callTool<WebexMutedSpace>('unmute_space', { space_id })
}

export function listMutedSpaces(): Promise<WebexMutedSpace[]> {
  return callTool<WebexMutedSpace[]>('list_muted_spaces')
}
