import { callTool } from './mcp'

export type ReportRange = {
  from: string
  to: string
}

export type ReportResult = {
  markdown: string
  citations: number[]
  range?: ReportRange
  mode?: string
  error?: string
}

export function reportDaily(date?: string, project?: string): Promise<ReportResult> {
  return callTool<ReportResult>('report_daily', {
    ...(date ? { date } : {}),
    ...(project ? { project } : {}),
  })
}

export function reportWeekly(weekEnd?: string, project?: string): Promise<ReportResult> {
  return callTool<ReportResult>('report_weekly', {
    ...(weekEnd ? { week_end: weekEnd } : {}),
    ...(project ? { project } : {}),
  })
}

export function reportMonthly(month?: string, project?: string): Promise<ReportResult> {
  return callTool<ReportResult>('report_monthly', {
    ...(month ? { month } : {}),
    ...(project ? { project } : {}),
  })
}

export function reportQuery(input: {
  q: string
  project?: string
  since?: string
  until?: string
}): Promise<ReportResult> {
  return callTool<ReportResult>('report_query', input)
}
