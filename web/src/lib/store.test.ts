import { beforeEach, describe, expect, it } from 'vitest'
import { useUiStore } from './store'

describe('todo draft store', () => {
  beforeEach(() => {
    useUiStore.setState({ addTodoOpen: false, todoDraft: null, settingsOpen: false, settingsTab: 'connections' })
  })

  it('opens the todo dialog with source context', () => {
    const draft = {
      title: 'Review CXP-77',
      description: 'Tracked from [JIRA:CXP-77]',
      external_source: 'jira',
      external_ref: 'CXP-77',
      jira_ref: 'CXP-77',
    }
    useUiStore.getState().openAddTodo(draft)
    expect(useUiStore.getState().addTodoOpen).toBe(true)
    expect(useUiStore.getState().todoDraft).toEqual(draft)
  })

  it('keeps an edit task in the draft when opening edit mode', () => {
    const edit = {
      id: 42,
      title: 'Patch the queue',
      priority: 2 as const,
      is_completed: false,
      domain: 'work' as const,
      source: 'manual' as const,
      goal_id: 7,
      jira_ref: 'CXP-42',
      recurrence_rule: 'FREQ=WEEKLY',
    }
    useUiStore.getState().openAddTodo({ edit })
    expect(useUiStore.getState().todoDraft?.edit).toEqual(edit)
  })

  it('opens settings from the shared UI store', () => {
    useUiStore.getState().setSettingsOpen(true)
    useUiStore.getState().setSettingsTab('projects')
    expect(useUiStore.getState().settingsOpen).toBe(true)
    expect(useUiStore.getState().settingsTab).toBe('projects')
  })
})
