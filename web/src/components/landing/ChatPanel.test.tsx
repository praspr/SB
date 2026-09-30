import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { ChatPanelView } from './ChatPanel'

describe('landing chat', () => {
  it('shows grounded messages and suggested questions', () => {
    const html = renderToStaticMarkup(
      <ChatPanelView
        messages={[
          { role: 'user', content: 'What is blocked?' },
          {
            role: 'assistant',
            content: 'Routing is blocked. [JIRA:CXP-42]',
            citations: ['[JIRA:CXP-42]'],
          },
        ]}
        question=""
        pending={false}
        onQuestion={() => undefined}
        onSubmit={() => undefined}
        onSuggestion={() => undefined}
      />,
    )
    expect(html).toContain('Ask your second brain')
    expect(html).toContain('Routing is blocked.')
    expect(html).toContain('[JIRA:CXP-42]')
    expect(html).toContain('Read-only')

    const empty = renderToStaticMarkup(
      <ChatPanelView
        messages={[]}
        question=""
        pending={false}
        onQuestion={() => undefined}
        onSubmit={() => undefined}
        onSuggestion={() => undefined}
      />,
    )
    expect(empty).toContain('What should I focus on today?')
  })

  it('calls ask_sb through the MCP client', async () => {
    vi.resetModules()
    vi.doMock('@/lib/mcp', () => ({ callTool: vi.fn() }))
    const mcp = await import('@/lib/mcp')
    vi.mocked(mcp.callTool).mockResolvedValue({
      answer: 'One task is due. [todo:1]',
      citations: ['[todo:1]'],
      mode: 'llm',
    })
    const { askSecondBrain } = await import('@/lib/chat')
    await askSecondBrain('What is due?')
    expect(mcp.callTool).toHaveBeenCalledWith('ask_sb', { question: 'What is due?' })
  })
})

