import { callTool } from './mcp'

export type UrlHint = {
  kind: 'jira' | 'webex' | 'github' | 'file' | 'generic'
  extracted: Record<string, unknown>
  suggested_action: 'track_jira' | 'open_space' | 'attach_as_ref'
}

export function parseUrlHint(url: string): Promise<UrlHint> {
  return callTool<UrlHint>('parse_url_hint', { url })
}
