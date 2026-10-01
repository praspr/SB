import { QueryClient } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Task } from './mock-data'

vi.mock('./mcp', () => ({
  callTool: vi.fn(),
}))

const sample = {
  id: 7,
  title: 'Write the note',
  description: '',
  priority: 2,
  due_date: null,
  due_time: null,
  is_completed: false,
  completed_at: null,
  tags: [],
  external_source: null,
  external_ref: null,
  domain: 'work',
  created_at: '2026-09-30T00:00:00Z',
  updated_at: '2026-09-30T00:00:00Z',
}

describe('todo queries', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('lists todos returned by the MCP tool', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([sample])
    const { fetchTasks } = await import('./queries')
    const tasks = await fetchTasks()
    expect(callTool).toHaveBeenCalledWith('todo_list', { status: 'all' })
    expect(tasks).toEqual([
      expect.objectContaining({ id: 7, title: 'Write the note', is_completed: false, priority: 2 }),
    ])
  })

  it('adds a todo through todo_add', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue(sample)
    const { createTask } = await import('./queries')
    const task = await createTask({ title: 'Write the note', priority: 2, domain: 'work' })
    expect(callTool).toHaveBeenCalledWith('todo_add', {
      title: 'Write the note',
      priority: 2,
      domain: 'work',
    })
    expect(task.title).toBe('Write the note')
  })

  it('optimistically completes a task and rolls the cache back when MCP fails', async () => {
    const { markTaskCompleted, restoreSnapshots } = await import('./queries')
    const client = new QueryClient()
    const open: Task = {
      id: 7,
      title: 'Write the note',
      priority: 2,
      is_completed: false,
      domain: 'work',
      source: 'manual',
    }
    client.setQueryData(['tasks'], [open])
    const previous = client.getQueriesData<Task[]>({ queryKey: ['tasks'] })

    client.setQueriesData<Task[]>({ queryKey: ['tasks'] }, (old) => markTaskCompleted(old, 7))
    expect(client.getQueryData<Task[]>(['tasks'])?.[0].is_completed).toBe(true)

    restoreSnapshots(client, previous)
    expect(client.getQueryData<Task[]>(['tasks'])?.[0].is_completed).toBe(false)
  })

  it('updates a todo through todo_update', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue(sample)
    const { updateTask } = await import('./queries')
    await updateTask(7, { title: 'Updated title', goal_id: null, jira_ref: null, recurrence_rule: null })
    expect(callTool).toHaveBeenCalledWith('todo_update', {
      todo_id: 7,
      title: 'Updated title',
      goal_id: null,
      jira_ref: null,
      recurrence_rule: null,
    })
  })
})
