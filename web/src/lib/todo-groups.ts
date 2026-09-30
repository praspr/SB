import type { Priority, Task } from './mock-data'

export type TodoStatusFilter = 'all' | 'open' | 'completed'
export type TodoSort = 'priority' | 'due' | 'title'

export type TodoGroup = {
  key: 'today' | 'upcoming' | 'no-date' | 'completed'
  label: string
  tasks: Task[]
}

type OrganizeOptions = {
  status: TodoStatusFilter
  priority: Priority | 'all'
  query: string
  sort: TodoSort
  today: string
}

export function summarizeTodos(tasks: Task[], today: string) {
  const open = tasks.filter((task) => !task.is_completed)
  return {
    overdue: open.filter((task) => task.due_date && task.due_date < today).length,
    today: open.filter((task) => task.due_date === today).length,
    open: open.length,
    completed: tasks.length - open.length,
  }
}

function compareTasks(sort: TodoSort) {
  return (a: Task, b: Task) => {
    if (sort === 'title') return a.title.localeCompare(b.title)
    if (sort === 'due') {
      const dueOrder = (a.due_date ?? '9999-12-31').localeCompare(b.due_date ?? '9999-12-31')
      return dueOrder || a.priority - b.priority
    }
    return a.priority - b.priority || (a.due_date ?? '9999-12-31').localeCompare(b.due_date ?? '9999-12-31')
  }
}

function matchesQuery(task: Task, query: string): boolean {
  if (!query) return true
  const searchable = [
    task.title,
    task.description,
    task.domain,
    task.source,
    task.ref,
    task.jira_ref,
  ].filter(Boolean).join(' ').toLowerCase()
  return searchable.includes(query)
}

export function organizeTodos(tasks: Task[], options: OrganizeOptions): TodoGroup[] {
  const query = options.query.trim().toLowerCase()
  const filtered = tasks
    .filter((task) => options.status === 'all'
      || (options.status === 'open' ? !task.is_completed : task.is_completed))
    .filter((task) => options.priority === 'all' || task.priority === options.priority)
    .filter((task) => matchesQuery(task, query))
    .sort(compareTasks(options.sort))

  const open = filtered.filter((task) => !task.is_completed)
  const completed = filtered.filter((task) => task.is_completed)
  const groups: TodoGroup[] = [
    {
      key: 'today',
      label: 'Today',
      tasks: open.filter((task) => Boolean(task.due_date && task.due_date <= options.today)),
    },
    {
      key: 'upcoming',
      label: 'Upcoming',
      tasks: open.filter((task) => Boolean(task.due_date && task.due_date > options.today)),
    },
    {
      key: 'no-date',
      label: 'No date',
      tasks: open.filter((task) => !task.due_date),
    },
    {
      key: 'completed',
      label: 'Completed',
      tasks: completed,
    },
  ]
  return groups.filter((group) => group.tasks.length > 0)
}
