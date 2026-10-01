import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { listJiraTickets, TASKS_QUERY_KEY, useUpdateTask } from '@/lib/queries'
import { listGoalsV2 } from '@/lib/goals'
import { createRichTask } from '@/lib/todos-rich'
import { useUiStore } from '@/lib/store'
import type { Priority, Task } from '@/lib/mock-data'

export function AddTodoDialog() {
  const open = useUiStore((s) => s.addTodoOpen)
  const draft = useUiStore((s) => s.todoDraft)
  const setOpen = useUiStore((s) => s.setAddTodoOpen)
  const client = useQueryClient()
  const updateTask = useUpdateTask()
  const editing = draft?.edit
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<Priority>(2)
  const [domain, setDomain] = useState<Task['domain']>('work')
  const [goalId, setGoalId] = useState('')
  const [jiraRef, setJiraRef] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [dueTime, setDueTime] = useState('')
  const [remindBeforeMinutes, setRemindBeforeMinutes] = useState('0')
  const [recurrencePreset, setRecurrencePreset] = useState('')
  const [customRrule, setCustomRrule] = useState('')
  const goals = useQuery({ queryKey: ['goals-v2', 'dialog'], queryFn: async () => listGoalsV2(), staleTime: 30_000, enabled: open })
  const jiraTickets = useQuery({ queryKey: ['jira-dialog'], queryFn: () => listJiraTickets({ limit: 200 }), staleTime: 30_000, enabled: open })

  useEffect(() => {
    if (!open) return
    const source = editing ?? draft
    setTitle(source?.title ?? '')
    setDescription(source?.description ?? '')
    setPriority(source?.priority ?? 2)
    setDomain(editing?.domain ?? 'work')
    setGoalId(editing?.goal_id ? String(editing.goal_id) : draft?.goal_id ? String(draft.goal_id) : '')
    setJiraRef(source?.jira_ref ?? '')
    setDueDate(source?.due_date ?? '')
    setDueTime(source?.due_time ?? '')
    setRemindBeforeMinutes(String(source?.remind_before_minutes ?? 0))
    const recurrence = editing?.recurrence_rule ?? draft?.recurrence_rule ?? ''
    if (recurrence === 'FREQ=DAILY' || recurrence === 'FREQ=WEEKLY' || recurrence === 'FREQ=MONTHLY') {
      setRecurrencePreset(recurrence)
      setCustomRrule('')
    } else if (recurrence) {
      setRecurrencePreset('custom')
      setCustomRrule(recurrence)
    } else {
      setRecurrencePreset('')
      setCustomRrule('')
    }
  }, [open, draft, editing])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    const recurrence_rule = recurrencePreset === 'custom' ? customRrule.trim() || undefined : recurrencePreset || undefined
    const normalizedDueDate = dueDate || null
    const normalizedDueTime = normalizedDueDate && dueTime ? dueTime : null
    const rawRemind = Number(remindBeforeMinutes)
    const normalizedRemindBeforeMinutes =
      normalizedDueDate && normalizedDueTime
        ? Math.min(1440, Math.max(0, Number.isFinite(rawRemind) ? rawRemind : 0))
        : null
    const payload = {
      title: title.trim(),
      description: description.trim() || undefined,
      priority,
      due_date: normalizedDueDate,
      due_time: normalizedDueTime,
      remind_before_minutes: normalizedRemindBeforeMinutes,
      domain,
      goal_id: goalId ? Number(goalId) : null,
      jira_ref: jiraRef.trim() || null,
      recurrence_rule: recurrence_rule ?? null,
    }
    const request = editing
      ? updateTask.mutateAsync({ taskId: editing.id, patch: payload })
      : createRichTask({
          ...payload,
          due_date: normalizedDueDate ?? undefined,
          due_time: normalizedDueTime ?? undefined,
          remind_before_minutes: normalizedRemindBeforeMinutes ?? undefined,
          goal_id: goalId ? Number(goalId) : undefined,
          jira_ref: jiraRef.trim() || undefined,
          recurrence_rule,
          external_source: draft?.external_source,
          external_ref: draft?.external_ref,
        })
    void request.then(() => {
      void client.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
    })
    setTitle('')
    setDescription('')
    setPriority(2)
    setDueDate('')
    setDueTime('')
    setRemindBeforeMinutes('0')
    setDomain('work')
    setGoalId('')
    setJiraRef('')
    setRecurrencePreset('')
    setCustomRrule('')
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogTitle>{editing ? 'Edit todo' : 'New todo'}</DialogTitle>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="mb-1 block text-12 text-text-secondary">Title</label>
            <Input
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What needs to get done?"
            />
          </div>
          <div>
            <label className="mb-1 block text-12 text-text-secondary">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-border-subtle bg-bg-panel px-3 py-2 text-13 text-text-primary outline-none focus:border-accent-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-12 text-text-secondary">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value) as Priority)}
                className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-2 text-13 text-text-primary outline-none focus:border-accent-500"
              >
                <option value={1}>1 — Highest</option>
                <option value={2}>2 — High</option>
                <option value={3}>3 — Medium</option>
                <option value={4}>4 — Low</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-12 text-text-secondary">Domain</label>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value as Task['domain'])}
                className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-2 text-13 text-text-primary outline-none focus:border-accent-500"
              >
                <option value="work">Work</option>
                <option value="learning">Learning</option>
                <option value="personal">Personal</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-12 text-text-secondary">Goal</label>
              <select value={goalId} onChange={(e) => setGoalId(e.target.value)} className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-2 text-13 text-text-primary outline-none focus:border-accent-500">
                <option value="">None</option>
                {(goals.data ?? []).map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-12 text-text-secondary">JIRA key</label>
              <>
                <Input list="jira-ticket-keys" value={jiraRef} onChange={(e) => setJiraRef(e.target.value)} placeholder="CXP-12345" />
                <datalist id="jira-ticket-keys">
                  {(jiraTickets.data ?? []).map((ticket) => <option key={ticket.key} value={ticket.key} />)}
                </datalist>
              </>
            </div>
          </div>
          <div className="rounded-xl border border-border-subtle bg-black/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <label className="block text-12 uppercase tracking-[0.18em] text-text-muted">Due</label>
                <div className="mt-1 text-12 text-text-secondary">Leave time empty for a date-only todo (no alert).</div>
              </div>
              {dueDate ? (
                <button
                  type="button"
                  onClick={() => {
                    setDueDate('')
                    setDueTime('')
                    setRemindBeforeMinutes('0')
                  }}
                  className="rounded-full border border-border-subtle px-2.5 py-1 text-12 text-text-muted transition-colors duration-fast ease-out hover:border-border-strong hover:text-text-primary"
                >
                  Clear
                </button>
              ) : null}
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label>
                <div className="mb-1 text-12 text-text-secondary">Date</div>
                <input
                  type="date"
                  aria-label="Due date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-3 text-13 text-text-primary outline-none focus:border-accent-500"
                />
              </label>
              {dueDate ? (
                <label>
                  <div className="mb-1 text-12 text-text-secondary">Time</div>
                  <input
                    type="time"
                    aria-label="Due time"
                    value={dueTime}
                    onChange={(e) => setDueTime(e.target.value)}
                    className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-3 text-13 text-text-primary outline-none focus:border-accent-500"
                  />
                </label>
              ) : null}
            </div>
            {dueDate && dueTime ? (
              <label className="mt-3 block">
                <div className="mb-1 text-12 text-text-secondary">Remind me N minutes before</div>
                <input
                  type="number"
                  min={0}
                  max={1440}
                  aria-label="Remind me minutes before"
                  value={remindBeforeMinutes}
                  onChange={(e) => setRemindBeforeMinutes(e.target.value)}
                  className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-3 text-13 text-text-primary outline-none focus:border-accent-500"
                />
              </label>
            ) : null}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-12 text-text-secondary">Recurrence</label>
              <select value={recurrencePreset} onChange={(e) => setRecurrencePreset(e.target.value)} className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-2 text-13 text-text-primary outline-none focus:border-accent-500">
                <option value="">None</option>
                <option value="FREQ=DAILY">Daily</option>
                <option value="FREQ=WEEKLY">Weekly</option>
                <option value="FREQ=MONTHLY">Monthly</option>
                <option value="custom">Custom (RRULE)</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-12 text-text-secondary">Custom RRULE</label>
              <Input value={customRrule} onChange={(e) => setCustomRrule(e.target.value)} placeholder="FREQ=WEEKLY;BYDAY=MO,WE" disabled={recurrencePreset !== 'custom'} />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              {editing ? 'Save changes' : 'Add todo'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
