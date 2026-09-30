export type Priority = 1 | 2 | 3 | 4 // 1 = highest, matches sb backend

export type Task = {
  id: number
  title: string
  description?: string
  priority: Priority
  due_date?: string // ISO YYYY-MM-DD
  due_time?: string // HH:MM (sb_due_time)
  is_completed: boolean
  domain: 'work' | 'learning' | 'personal'
  source: 'jira' | 'manual' | 'changelog'
  ref?: string // e.g. 'CXP-45827'
  rationale?: string // sb_rationale
  score?: number
}

export type Meeting = {
  id: string
  title: string
  start: string // ISO datetime with timezone
  end: string
  attendees: { name: string; email: string; avatar?: string }[]
  location?: string
  join_url?: string
  is_organizer: boolean
  agenda?: string
}

export type WebexMessage = {
  id: string
  from: { name: string; email: string; avatar?: string }
  space: string // space name or DM
  space_id: string
  is_dm: boolean
  is_mention: boolean
  is_unread: boolean
  preview: string // first ~100 chars
  ts: string // ISO datetime
}

export type WebexSpace = {
  id: string
  name: string
  is_dm: boolean
  unread_count: number
  last_activity: string // ISO datetime
  members_count: number
}

export type JiraStatus =
  | 'Open'
  | 'In Progress'
  | 'In Engineering Review'
  | 'Code Review'
  | 'Dev Complete'
  | 'In Testing'
  | 'Test Complete'
  | 'Pending Approval'
  | 'Blocked'
  | 'Done'
  | 'Resolved'
  | 'Closed'
  | 'Cancelled'

export type JiraPriority = 'Highest' | 'High' | 'Medium' | 'Low' | 'Lowest'

export type JiraTicket = {
  key: string // 'CXP-45827'
  project: string // 'CXP'
  title: string
  status: JiraStatus
  priority: JiraPriority
  issue_type: string // 'Bug', 'Task', 'Story', 'Epic'
  assignee: {
    name: string
    email: string
  }
  reporter?: {
    name: string
    email: string
  }
  created: string // ISO datetime
  updated: string // ISO datetime
  labels: string[]
  fix_versions: string[]
  description: string // short summary text (mock)
  url: string // https://cisco-cxe.atlassian.net/browse/CXP-45827
  file_path?: string // 'ciq/docs/jira/tickets/CXP-45827.md'
}

// --- helpers to build relative dates so "today" fixtures always work ---
function isoDate(offsetDays: number): string {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  return d.toISOString().slice(0, 10)
}

function isoDateTime(offsetDays: number, hour: number, minute = 0): string {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  d.setHours(hour, minute, 0, 0)
  return d.toISOString()
}

const today = isoDate(0)
const tomorrow = isoDate(1)
const yesterday = isoDate(-1)

export const mockTasks: Task[] = [
  {
    id: 1,
    title: 'CXP-45827 — Reduce backlog below target',
    description: 'Close out the assigned ticket queue before it breaches SLA.',
    priority: 1,
    due_date: today,
    is_completed: false,
    domain: 'work',
    source: 'jira',
    ref: 'CXP-45827',
    rationale: 'Highest rank: matches weekly goal to keep tickets under 10, overdue, strong work weight.',
    score: 91,
  },
  {
    id: 2,
    title: 'Draft wrap notes before 16:30',
    priority: 1,
    due_date: today,
    due_time: '16:30',
    is_completed: false,
    domain: 'work',
    source: 'manual',
    rationale: 'Creates clean evidence while context is fresh.',
    score: 84,
  },
  {
    id: 3,
    title: 'Review pending CHANGELOG proposal batch',
    priority: 2,
    due_date: today,
    is_completed: false,
    domain: 'work',
    source: 'changelog',
    rationale: 'Unblocks queued remote-facing outputs.',
    score: 79,
  },
  {
    id: 4,
    title: 'CXP-45831 — Investigate flaky ranker test',
    priority: 2,
    due_date: today,
    is_completed: false,
    domain: 'work',
    source: 'jira',
    ref: 'CXP-45831',
    score: 71,
  },
  {
    id: 5,
    title: 'Read chapter 4 of "Staff Engineer"',
    priority: 3,
    due_date: tomorrow,
    is_completed: false,
    domain: 'learning',
    source: 'manual',
    score: 52,
  },
  {
    id: 6,
    title: 'Schedule dentist appointment',
    priority: 3,
    due_date: tomorrow,
    is_completed: false,
    domain: 'personal',
    source: 'manual',
    score: 45,
  },
  {
    id: 7,
    title: 'CXP-45810 — Follow up with design on spacing tokens',
    priority: 2,
    due_date: yesterday,
    is_completed: false,
    domain: 'work',
    source: 'jira',
    ref: 'CXP-45810',
    score: 68,
  },
  {
    id: 8,
    title: 'Clean up changelog formatting script',
    priority: 4,
    is_completed: true,
    domain: 'work',
    source: 'changelog',
    score: 30,
  },
]

export const mockMeetings: Meeting[] = [
  {
    id: 'm1',
    title: 'Daily standup',
    start: isoDateTime(0, 9, 0),
    end: isoDateTime(0, 9, 15),
    attendees: [
      { name: 'Priya Raman', email: 'priya@example.com' },
      { name: 'Alex Chen', email: 'alex@example.com' },
      { name: 'Sam Okafor', email: 'sam@example.com' },
    ],
    join_url: 'https://webex.com/meet/standup',
    is_organizer: false,
  },
  {
    id: 'm2',
    title: '1:1 with manager',
    start: isoDateTime(0, 11, 0),
    end: isoDateTime(0, 11, 30),
    attendees: [{ name: 'Jordan Lee', email: 'jordan@example.com' }],
    join_url: 'https://webex.com/meet/1on1',
    is_organizer: false,
  },
  {
    id: 'm3',
    title: 'Backlog grooming — CXP',
    start: isoDateTime(0, 13, 30),
    end: isoDateTime(0, 14, 15),
    attendees: [
      { name: 'Priya Raman', email: 'priya@example.com' },
      { name: 'Wei Zhang', email: 'wei@example.com' },
      { name: 'Dana Kim', email: 'dana@example.com' },
      { name: 'Sam Okafor', email: 'sam@example.com' },
    ],
    location: 'Conf Room 4B',
    is_organizer: true,
  },
  {
    id: 'm4',
    title: 'Design system sync',
    start: isoDateTime(0, 16, 0),
    end: isoDateTime(0, 16, 45),
    attendees: [
      { name: 'Alex Chen', email: 'alex@example.com' },
      { name: 'Noor Habib', email: 'noor@example.com' },
    ],
    join_url: 'https://webex.com/meet/design-sync',
    is_organizer: false,
    agenda: 'Review spacing tokens and dark theme contrast.',
  },
  {
    id: 'm5',
    title: 'Sprint planning',
    start: isoDateTime(1, 10, 0),
    end: isoDateTime(1, 11, 0),
    attendees: [
      { name: 'Priya Raman', email: 'priya@example.com' },
      { name: 'Jordan Lee', email: 'jordan@example.com' },
      { name: 'Wei Zhang', email: 'wei@example.com' },
    ],
    join_url: 'https://webex.com/meet/sprint-planning',
    is_organizer: false,
  },
  {
    id: 'm6',
    title: 'JIRA token setup with IT',
    start: isoDateTime(1, 13, 0),
    end: isoDateTime(1, 13, 30),
    attendees: [{ name: 'IT Support', email: 'it@example.com' }],
    is_organizer: true,
  },
  {
    id: 'm7',
    title: 'Architecture review',
    start: isoDateTime(1, 14, 30),
    end: isoDateTime(1, 15, 30),
    attendees: [
      { name: 'Dana Kim', email: 'dana@example.com' },
      { name: 'Sam Okafor', email: 'sam@example.com' },
      { name: 'Noor Habib', email: 'noor@example.com' },
    ],
    join_url: 'https://webex.com/meet/arch-review',
    is_organizer: false,
  },
  {
    id: 'm8',
    title: 'Coffee chat: onboarding buddy',
    start: isoDateTime(1, 9, 30),
    end: isoDateTime(1, 9, 45),
    attendees: [{ name: 'New Hire', email: 'newhire@example.com' }],
    is_organizer: true,
  },
  {
    id: 'm9',
    title: 'Q3 goals check-in',
    start: isoDateTime(1, 16, 0),
    end: isoDateTime(1, 16, 30),
    attendees: [{ name: 'Jordan Lee', email: 'jordan@example.com' }],
    join_url: 'https://webex.com/meet/goals',
    is_organizer: false,
  },
  {
    id: 'm10',
    title: 'Changelog proposal walkthrough',
    start: isoDateTime(1, 11, 30),
    end: isoDateTime(1, 12, 0),
    attendees: [
      { name: 'Priya Raman', email: 'priya@example.com' },
      { name: 'Alex Chen', email: 'alex@example.com' },
    ],
    is_organizer: true,
  },
]

export const mockWebexMessages: WebexMessage[] = [
  {
    id: 'w1',
    from: { name: 'Priya Raman', email: 'priya@example.com' },
    space: 'Priya Raman',
    space_id: 'dm-priya',
    is_dm: true,
    is_mention: false,
    is_unread: true,
    preview: 'Hey, did you get a chance to look at the ranker PR?',
    ts: isoDateTime(0, 8, 40),
  },
  {
    id: 'w2',
    from: { name: 'Alex Chen', email: 'alex@example.com' },
    space: 'Alex Chen',
    space_id: 'dm-alex',
    is_dm: true,
    is_mention: false,
    is_unread: true,
    preview: 'Design tokens are updated, take a look when you can.',
    ts: isoDateTime(0, 9, 55),
  },
  {
    id: 'w3',
    from: { name: 'Wei Zhang', email: 'wei@example.com' },
    space: 'CXP Backlog',
    space_id: 'space-cxp',
    is_dm: false,
    is_mention: true,
    is_unread: true,
    preview: '@you can you confirm the priority on CXP-45827 before standup?',
    ts: isoDateTime(0, 8, 10),
  },
  {
    id: 'w4',
    from: { name: 'Dana Kim', email: 'dana@example.com' },
    space: 'Architecture',
    space_id: 'space-arch',
    is_dm: false,
    is_mention: true,
    is_unread: false,
    preview: '@you great point in the review, can you write it up?',
    ts: isoDateTime(0, 15, 20),
  },
  {
    id: 'w5',
    from: { name: 'Sam Okafor', email: 'sam@example.com' },
    space: 'Sam Okafor',
    space_id: 'dm-sam',
    is_dm: true,
    is_mention: false,
    is_unread: false,
    preview: 'Thanks for the help debugging the flaky test earlier!',
    ts: isoDateTime(-1, 17, 5),
  },
]

export const mockWebexSpaces: WebexSpace[] = [
  { id: 'space-cxp', name: 'CXP Backlog', is_dm: false, unread_count: 3, last_activity: isoDateTime(0, 8, 10), members_count: 8 },
  { id: 'space-arch', name: 'Architecture', is_dm: false, unread_count: 1, last_activity: isoDateTime(0, 15, 20), members_count: 12 },
  { id: 'space-design', name: 'Design System', is_dm: false, unread_count: 0, last_activity: isoDateTime(-1, 12, 0), members_count: 6 },
  { id: 'space-general', name: 'General', is_dm: false, unread_count: 5, last_activity: isoDateTime(0, 10, 45), members_count: 34 },
  { id: 'dm-priya', name: 'Priya Raman', is_dm: true, unread_count: 1, last_activity: isoDateTime(0, 8, 40), members_count: 2 },
  { id: 'dm-alex', name: 'Alex Chen', is_dm: true, unread_count: 1, last_activity: isoDateTime(0, 9, 55), members_count: 2 },
]

function jiraUrl(key: string): string {
  return `https://cisco-cxe.atlassian.net/browse/${key}`
}

function jiraFilePath(key: string): string {
  return `ciq/docs/jira/tickets/${key}.md`
}

export const mockJiraTickets: JiraTicket[] = [
  {
    key: 'CXP-45827',
    project: 'CXP',
    title: 'Reduce backlog below target for BAQS ruleEvaluations queue',
    status: 'In Progress',
    priority: 'Highest',
    issue_type: 'Bug',
    assignee: { name: 'Priya Raman', email: 'priya@example.com' },
    reporter: { name: 'Jordan Lee', email: 'jordan@example.com' },
    created: isoDateTime(-19, 9, 12),
    updated: isoDateTime(-1, 14, 5),
    labels: ['ciq-config-tc-regress', 'baqs'],
    fix_versions: ['2026.09.1'],
    description: 'ruleEvaluations resolver is timing out under high asset scope filters; needs pagination fix.',
    url: jiraUrl('CXP-45827'),
    file_path: jiraFilePath('CXP-45827'),
  },
  {
    key: 'CXP-19735',
    project: 'CXP',
    title: 'text-to-SQL agent misinterprets compound WHERE clauses',
    status: 'In Engineering Review',
    priority: 'High',
    issue_type: 'Bug',
    assignee: { name: 'Alex Chen', email: 'alex@example.com' },
    reporter: { name: 'Dana Kim', email: 'dana@example.com' },
    created: isoDateTime(-24, 10, 0),
    updated: isoDateTime(-2, 16, 40),
    labels: ['text-to-sql', 'configbp-ai'],
    fix_versions: ['2026.09.1'],
    description: 'Agent drops the second predicate when a compound AND/OR filter is generated for findings queries.',
    url: jiraUrl('CXP-19735'),
    file_path: jiraFilePath('CXP-19735'),
  },
  {
    key: 'CXP-19023',
    project: 'CXP',
    title: 'expertInsights panel shows stale rule evaluation counts',
    status: 'Open',
    priority: 'Medium',
    issue_type: 'Bug',
    assignee: { name: 'Sam Okafor', email: 'sam@example.com' },
    reporter: { name: 'Wei Zhang', email: 'wei@example.com' },
    created: isoDateTime(-6, 11, 20),
    updated: isoDateTime(-3, 9, 15),
    labels: ['expert-insights', 'caching'],
    fix_versions: [],
    description: 'Expert insights cache is not invalidated after a new assessment execution completes.',
    url: jiraUrl('CXP-19023'),
    file_path: jiraFilePath('CXP-19023'),
  },
  {
    key: 'CXP-46012',
    project: 'CXP',
    title: 'Add asset_scope pre-filter support to configbp-ai MCP tools',
    status: 'Open',
    priority: 'High',
    issue_type: 'Story',
    assignee: { name: 'Dana Kim', email: 'dana@example.com' },
    reporter: { name: 'Noor Habib', email: 'noor@example.com' },
    created: isoDateTime(-10, 8, 45),
    updated: isoDateTime(-4, 13, 30),
    labels: ['configbp-ai', 'mcp'],
    fix_versions: ['2026.10.0'],
    description: 'All MCP tools must route asset filters through search_assets_scope before evaluation.',
    url: jiraUrl('CXP-46012'),
    file_path: jiraFilePath('CXP-46012'),
  },
  {
    key: 'CXP-45990',
    project: 'CXP',
    title: 'BAQS findings/findingsCount parity broken for SecurityHardening',
    status: 'In Testing',
    priority: 'Highest',
    issue_type: 'Bug',
    assignee: { name: 'Wei Zhang', email: 'wei@example.com' },
    reporter: { name: 'Priya Raman', email: 'priya@example.com' },
    created: isoDateTime(-14, 9, 0),
    updated: isoDateTime(-1, 10, 10),
    labels: ['baqs', 'security-hardening'],
    fix_versions: ['2026.09.1'],
    description: 'findingsCount resolver returns a different total than findings pagination for SH category.',
    url: jiraUrl('CXP-45990'),
    file_path: jiraFilePath('CXP-45990'),
  },
  {
    key: 'CXP-30112',
    project: 'CXP',
    title: 'Priority Bugs AI: wire consumption tables for domain MCP tools',
    status: 'Blocked',
    priority: 'Medium',
    issue_type: 'Epic',
    assignee: { name: 'Jordan Lee', email: 'jordan@example.com' },
    reporter: { name: 'Alex Chen', email: 'alex@example.com' },
    created: isoDateTime(-45, 9, 0),
    updated: isoDateTime(-5, 15, 50),
    labels: ['priority-bugs-ai', 'trino'],
    fix_versions: [],
    description: 'Blocked on CXP-31945/CXP-31929 landing the consumption tables before agent wiring can proceed.',
    url: jiraUrl('CXP-30112'),
    file_path: jiraFilePath('CXP-30112'),
  },
  {
    key: 'CXP-45855',
    project: 'CXP',
    title: 'Add Trino tunnel healthcheck to local_trino_setup.sh',
    status: 'Code Review',
    priority: 'Low',
    issue_type: 'Task',
    assignee: { name: 'Noor Habib', email: 'noor@example.com' },
    reporter: { name: 'Sam Okafor', email: 'sam@example.com' },
    created: isoDateTime(-8, 13, 0),
    updated: isoDateTime(-2, 11, 25),
    labels: ['tooling', 'configbp-ai'],
    fix_versions: ['2026.09.1'],
    description: 'Script should retry and print a clear error when the Trino tunnel fails to bind locally.',
    url: jiraUrl('CXP-45855'),
    file_path: jiraFilePath('CXP-45855'),
  },
  {
    key: 'CXP-45701',
    project: 'CXP',
    title: 'CBP Engine worker: Parquet findings write retries on S3 throttling',
    status: 'Dev Complete',
    priority: 'High',
    issue_type: 'Bug',
    assignee: { name: 'Priya Raman', email: 'priya@example.com' },
    reporter: { name: 'Dana Kim', email: 'dana@example.com' },
    created: isoDateTime(-16, 10, 30),
    updated: isoDateTime(-3, 14, 0),
    labels: ['assessment-unified-engine', 'worker'],
    fix_versions: ['2026.09.1'],
    description: 'Worker should apply exponential backoff on S3 503 SlowDown responses when writing findings.',
    url: jiraUrl('CXP-45701'),
    file_path: jiraFilePath('CXP-45701'),
  },
  {
    key: 'CXP-44980',
    project: 'CXP',
    title: 'ruleEvaluations query missing isFastLane flag in generated SQL',
    status: 'Resolved',
    priority: 'Medium',
    issue_type: 'Bug',
    assignee: { name: 'Alex Chen', email: 'alex@example.com' },
    reporter: { name: 'Wei Zhang', email: 'wei@example.com' },
    created: isoDateTime(-30, 9, 40),
    updated: isoDateTime(-6, 12, 15),
    labels: ['baqs', 'resolver'],
    fix_versions: ['2026.08.2'],
    description: 'Resolver now always sets isFastLane: true and catalog: postgresql for Configuration category.',
    url: jiraUrl('CXP-44980'),
    file_path: jiraFilePath('CXP-44980'),
  },
  {
    key: 'CXP-44512',
    project: 'CXP',
    title: 'Deprecate legacy /v1/insights endpoint after migration',
    status: 'Closed',
    priority: 'Low',
    issue_type: 'Task',
    assignee: { name: 'Sam Okafor', email: 'sam@example.com' },
    reporter: { name: 'Jordan Lee', email: 'jordan@example.com' },
    created: isoDateTime(-60, 9, 0),
    updated: isoDateTime(-9, 16, 0),
    labels: ['deprecation', 'api'],
    fix_versions: ['2026.08.1'],
    description: 'All consumers migrated to expertInsights v2; legacy endpoint removed from routing table.',
    url: jiraUrl('CXP-44512'),
    file_path: jiraFilePath('CXP-44512'),
  },
  {
    key: 'CXP-45102',
    project: 'CXPL',
    title: 'Certificate lifecycle notifications firing twice for renewed certs',
    status: 'Cancelled',
    priority: 'Lowest',
    issue_type: 'Bug',
    assignee: { name: 'Dana Kim', email: 'dana@example.com' },
    reporter: { name: 'Noor Habib', email: 'noor@example.com' },
    created: isoDateTime(-22, 11, 0),
    updated: isoDateTime(-7, 10, 45),
    labels: ['cert-management'],
    fix_versions: [],
    description: 'Duplicate was a config artifact from a test tenant; no fix needed, closed as not reproducible.',
    url: jiraUrl('CXP-45102'),
    file_path: jiraFilePath('CXP-45102'),
  },
  {
    key: 'CXP-46101',
    project: 'CXP',
    title: 'cvi-ai-a2a semantic router misclassifies BAQS perf questions',
    status: 'In Progress',
    priority: 'High',
    issue_type: 'Bug',
    assignee: { name: 'Wei Zhang', email: 'wei@example.com' },
    reporter: { name: 'Priya Raman', email: 'priya@example.com' },
    created: isoDateTime(-3, 8, 30),
    updated: isoDateTime(0, 9, 20),
    labels: ['cvi-ai-a2a', 'routing'],
    fix_versions: ['2026.10.0'],
    description: 'Router sends BAQS SLA questions to the general agent instead of the baqs-agent skill.',
    url: jiraUrl('CXP-46101'),
    file_path: jiraFilePath('CXP-46101'),
  },
]
