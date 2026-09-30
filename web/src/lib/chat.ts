import { callTool } from './mcp'

export type ChatAnswer = {
  answer: string
  citations: string[]
  mode: 'llm' | 'fallback' | 'no_context'
}

export function askSecondBrain(question: string): Promise<ChatAnswer> {
  return callTool<ChatAnswer>('ask_sb', { question })
}

