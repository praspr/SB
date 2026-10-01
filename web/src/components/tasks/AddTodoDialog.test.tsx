// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AddTodoDialog } from '@/components/tasks/AddTodoDialog'

const invalidateQueries = vi.fn()
const mutateAsync = vi.fn()
const createRichTask = vi.fn()

const uiState = {
  addTodoOpen: true,
  todoDraft: null as any,
  setAddTodoOpen: vi.fn(),
}

vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: [] }),
  useQueryClient: () => ({ invalidateQueries }),
}))

vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
}))

vi.mock('@/components/ui/input', () => ({
  Input: ({ ...props }: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => <button {...props}>{children}</button>,
}))

vi.mock('@/lib/queries', () => ({
  listJiraTickets: () => Promise.resolve([]),
  TASKS_QUERY_KEY: ['tasks'],
  useUpdateTask: () => ({ mutateAsync }),
}))

vi.mock('@/lib/goals', () => ({ listGoalsV2: () => Promise.resolve([]) }))
vi.mock('@/lib/todos-rich', () => ({ createRichTask }))
vi.mock('@/lib/store', () => ({
  useUiStore: (selector: (state: typeof uiState) => unknown) => selector(uiState),
}))

function change(input: Element | null, value: string) {
  if (!(input instanceof HTMLInputElement || input instanceof HTMLSelectElement || input instanceof HTMLTextAreaElement)) {
    throw new Error('Expected form control')
  }
  act(() => {
    input.value = value
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new Event('change', { bubbles: true }))
  })
}

describe('AddTodoDialog due picker', () => {
  let container: HTMLDivElement
  let root: Root

  beforeEach(() => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    uiState.addTodoOpen = true
    uiState.todoDraft = null
    uiState.setAddTodoOpen.mockReset()
    invalidateQueries.mockReset()
    mutateAsync.mockReset()
    createRichTask.mockReset()
    createRichTask.mockResolvedValue({ id: 1, title: 'Ship it' })
    mutateAsync.mockResolvedValue({ id: 1, title: 'Ship it' })
  })

  afterEach(() => {
    act(() => root.unmount())
    container.remove()
  })

  it('shows date, reveals time, and clears due fields', () => {
    act(() => {
      root.render(<AddTodoDialog />)
    })

    expect(container.textContent).toContain('Leave time empty for a date-only todo (no alert).')
    expect(container.querySelector('input[aria-label="Due time"]')).toBeNull()

    change(container.querySelector('input[aria-label="Due date"]'), '2026-10-05')
    expect((container.querySelector('input[aria-label="Due time"]') as HTMLInputElement | null)?.value).toBe('')

    change(container.querySelector('input[aria-label="Due time"]'), '15:30')
    expect((container.querySelector('input[aria-label="Remind me minutes before"]') as HTMLInputElement | null)?.value).toBe('0')

    act(() => {
      ;(Array.from(container.querySelectorAll('button')).find((button) => button.textContent === 'Clear') as HTMLButtonElement).click()
    })

    expect((container.querySelector('input[aria-label="Due date"]') as HTMLInputElement).value).toBe('')
    expect(container.querySelector('input[aria-label="Due time"]')).toBeNull()
    expect(container.querySelector('input[aria-label="Remind me minutes before"]')).toBeNull()
  })

  it('prefills edit values and submits due fields', async () => {
    uiState.todoDraft = {
      edit: {
        id: 42,
        title: 'Review rollout',
        description: 'Final pass',
        priority: 2,
        due_date: '2026-10-05',
        due_time: '15:30',
        remind_before_minutes: 25,
        is_completed: false,
        domain: 'work',
        source: 'manual',
      },
    }

    act(() => {
      root.render(<AddTodoDialog />)
    })

    expect((container.querySelector('input[aria-label="Due date"]') as HTMLInputElement).value).toBe('2026-10-05')
    expect((container.querySelector('input[aria-label="Due time"]') as HTMLInputElement).value).toBe('15:30')
    expect((container.querySelector('input[aria-label="Remind me minutes before"]') as HTMLInputElement).value).toBe('25')

    await act(async () => {
      ;(Array.from(container.querySelectorAll('button')).find((button) => button.textContent === 'Save changes') as HTMLButtonElement).click()
      await Promise.resolve()
    })

    expect(mutateAsync).toHaveBeenCalledWith({
      taskId: 42,
      patch: expect.objectContaining({
        due_date: '2026-10-05',
        due_time: '15:30',
        remind_before_minutes: 25,
      }),
    })
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['tasks'] })
  })
})
