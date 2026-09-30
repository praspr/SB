import { callTool } from './mcp'
import type { Meeting, Task } from './mock-data'
import type { JiraTicket } from './mock-data'
import type { LedgerEntry, LedgerLogInput, LedgerLogResult } from './ledger'
import { ledgerLog } from './ledger'

export type AttentionItem = {
  id: string
  space_id: string
  space_name: string
  sender_name: string
  sender_email?: string | null
  is_dm: boolean
  is_mention: boolean
  is_unread: boolean
  preview: string
  occurred_at: string
  deep_link?: string | null
  triage_kind: 'mention' | 'dm' | 'question' | string
  staleness_hours?: number | null
  suggested_action_verb: 'Discussed' | 'Reviewed' | string
}

export type PreMeetingContext = {
  meeting: {
    id?: string
    title?: string
    start_at?: string
    end_at?: string
    attendees?: Meeting['attendees']
    join_url?: string | null
  }
  recent_messages: AttentionItem[]
  recent_ledger: LedgerEntry[]
  related_jiras: string[]
  open_todos: Array<Pick<Task, 'id' | 'title' | 'priority'>>
}

export type ProposeMeetingNotesResult = {
  proposal_ids: number[]
  draft_count: number
}

export type RitualMarkdownResult = {
  markdown: string
  citations: number[]
  date?: string
}

export function webexAttentionRanked(limit = 30): Promise<AttentionItem[]> {
  return callTool<AttentionItem[]>('webex_attention_ranked', { limit })
}

export function preMeetingContext(meetingId: string): Promise<PreMeetingContext> {
  return callTool<PreMeetingContext>('pre_meeting_context', { meeting_id: meetingId })
}

export function proposeMeetingNotes(meetingId: string): Promise<ProposeMeetingNotesResult> {
  return callTool<ProposeMeetingNotesResult>('propose_meeting_notes', { meeting_id: meetingId })
}

export function logAttentionToLedger(input: LedgerLogInput): Promise<LedgerLogResult> {
  return ledgerLog(input)
}

export async function reportToday(date?: string): Promise<RitualMarkdownResult> {
  const result = await callTool<{ date: string; plan_md: string | null }>('plan_day', date ? { date } : {})
  return { markdown: result.plan_md || 'No plan yet.', citations: [], date: result.date }
}

export async function reportWrap(): Promise<RitualMarkdownResult> {
  const result = await callTool<{ date: string; wrap_md: string }>('wrap_day', { dry_run: false })
  return { markdown: result.wrap_md || 'No wrap yet.', citations: [], date: result.date }
}

export async function reportStandup(date?: string): Promise<RitualMarkdownResult> {
  const result = await callTool<{ date: string; bullets: string[] }>('standup', date ? { date } : {})
  return { markdown: result.bullets.map((bullet) => `- ${bullet}`).join('\n'), citations: [], date: result.date }
}
