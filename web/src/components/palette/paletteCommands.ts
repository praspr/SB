export type SlashCommandDef = {
  cmd: string
  label: string
  hint: string
  kind: 'navigate' | 'brief'
}

export const SLASH_COMMANDS: SlashCommandDef[] = [
  { cmd: '/plan', label: 'Open daily plan', hint: '/plan', kind: 'navigate' },
  { cmd: '/wrap', label: 'Open wrap report', hint: '/wrap', kind: 'navigate' },
  { cmd: '/standup', label: 'Open standup report', hint: '/standup', kind: 'navigate' },
  { cmd: '/brief', label: "Run today's brief inline", hint: '/brief', kind: 'brief' },
  { cmd: '/goals', label: 'Open goals', hint: '/goals', kind: 'navigate' },
  { cmd: '/attention', label: 'Open attention inbox', hint: '/attention', kind: 'navigate' },
  { cmd: '/ledger', label: 'Search the ledger', hint: '/ledger <query>', kind: 'navigate' },
]

/** Pure: split "/ledger foo bar" into { cmd: '/ledger', arg: 'foo bar' }. */
export function parseSlashInput(query: string): { cmd: string; arg: string } {
  const trimmed = query.trimStart()
  const spaceIndex = trimmed.indexOf(' ')
  if (spaceIndex === -1) return { cmd: trimmed, arg: '' }
  return { cmd: trimmed.slice(0, spaceIndex), arg: trimmed.slice(spaceIndex + 1).trim() }
}

/** Pure: commands whose name starts with the typed command token. Typing the
 * full command name (e.g. "/ledger foo") still matches exactly that command. */
export function matchSlashCommands(query: string): SlashCommandDef[] {
  if (!query.startsWith('/')) return []
  const { cmd } = parseSlashInput(query)
  return SLASH_COMMANDS.filter((entry) => entry.cmd.startsWith(cmd))
}

/** Pure: the route to navigate to for a matched navigate-kind slash command,
 * or null when the command has no direct route (e.g. /brief runs inline). */
export function buildSlashRoute(cmd: string, arg: string): string | null {
  if (cmd === '/plan') return '/reports?template=daily'
  if (cmd === '/wrap') return '/reports?template=wrap'
  if (cmd === '/standup') return '/reports?template=standup'
  if (cmd === '/goals') return '/goals'
  if (cmd === '/attention') return '/attention'
  if (cmd === '/ledger') return `/ledger?q=${encodeURIComponent(arg)}`
  return null
}

const URL_LIKE_RE = /^(https?:\/\/|webexteams:\/\/|file:\/\/)/i

/** Pure: true when the query looks like a URL we should classify via parseUrlHint. */
export function isUrlLikeQuery(query: string): boolean {
  return URL_LIKE_RE.test(query.trim())
}

type BriefResult = { markdown?: string; error?: string }

/** Pure: pick the markdown to display for a successful /brief call. */
export function formatBriefResult(result: BriefResult): string {
  return result.markdown || result.error || 'No brief available.'
}

/** Pure: message to display when the /brief call itself throws. */
export function formatBriefError(error: unknown): string {
  return error instanceof Error ? error.message : 'Could not run brief.'
}

/** Run the /brief command inline: fetch today's daily report and return the
 * markdown (or a fallback message) to show in a dialog. Never throws --
 * transport/tool errors are converted into a display string. */
export async function runBriefReport(fetchDaily: () => Promise<BriefResult>): Promise<string> {
  try {
    const result = await fetchDaily()
    return formatBriefResult(result)
  } catch (error) {
    return formatBriefError(error)
  }
}
