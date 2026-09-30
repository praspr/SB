import { callTool } from './mcp'

export type Standup = {
  date: string
  bullets: string[]
}

export function getStandup(date?: string): Promise<Standup> {
  return callTool<Standup>('standup', date ? { date } : {})
}

export function standupText(bullets: string[]): string {
  return bullets.map((bullet) => `- ${bullet}`).join('\n')
}
