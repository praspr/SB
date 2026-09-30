import { callTool } from './mcp'

export type BulkJiraImportResult = {
  imported: number
  skipped: number
  ticket_keys: string[]
}

export function bulkImportJiraToTodos(input: {
  project?: string
  statuses?: string[]
  dry_run?: boolean
}): Promise<BulkJiraImportResult> {
  return callTool<BulkJiraImportResult>('bulk_import_jira_to_todos', input)
}
