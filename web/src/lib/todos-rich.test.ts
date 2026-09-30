import { describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({ callTool: vi.fn() }))

describe('rich todo creation', () => {
  it('passes source citations to the idempotent todo tool', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue({
      id: 1,
      title: 'Review CXP-77',
      description: 'Tracked from [JIRA:CXP-77]',
      priority: 2,
      due_date: null,
      due_time: null,
      is_completed: false,
      domain: 'work',
      external_source: 'jira',
      external_ref: 'CXP-77',
      goal_id: null,
      jira_ref: 'CXP-77',
      recurrence_rule: null,
    })
    const { createRichTask } = await import('./todos-rich')
    await createRichTask({
      title: 'Review CXP-77',
      description: 'Tracked from [JIRA:CXP-77]',
      priority: 2,
      domain: 'work',
      external_source: 'jira',
      external_ref: 'CXP-77',
      jira_ref: 'CXP-77',
    })
    expect(callTool).toHaveBeenCalledWith(
      'todo_add',
      expect.objectContaining({
        description: 'Tracked from [JIRA:CXP-77]',
        external_source: 'jira',
        external_ref: 'CXP-77',
        jira_ref: 'CXP-77',
      }),
    )
  })
})
