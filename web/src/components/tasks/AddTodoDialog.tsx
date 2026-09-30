import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { listJiraTickets } from '@/lib/queries'
import { listGoalsV2 } from '@/lib/goals'
import { createRichTask } from '@/lib/todos-rich'
import { useUiStore } from '@/lib/store'
import type { Priority, Task } from '@/lib/mock-data'

export function AddTodoDialog() {
  const open = useUiStore((s) => s.addTodoOpen)
  const setOpen = useUiStore((s) => s.setAddTodoOpen)
  const client = useQueryClient()
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState<Priority>(2)
  const [domain, setDomain] = useState<Task['domain']>('work')
  const [goalId, setGoalId] = useState('')
  const [jiraRef, setJiraRef] = useState('')
  const [recurrencePreset, setRecurrencePreset] = useState('')
  const [customRrule, setCustomRrule] = useState('')
  const goals = useQuery({ queryKey: ['goals-v2', 'dialog'], queryFn: async () => listGoalsV2(), staleTime: 30_000, enabled: open })
  const jiraTickets = useQuery({ queryKey: ['jira-dialog'], queryFn: () => listJiraTickets({ limit: 200 }), staleTime: 30_000, enabled: open })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    const recurrence_rule = recurrencePreset === 'custom' ? customRrule.trim() || undefined : recurrencePreset || undefined
    void createRichTask({
      title: title.trim(),
      priority,
      domain,
      goal_id: goalId ? Number(goalId) : undefined,
      jira_ref: jiraRef.trim() || undefined,
      recurrence_rule,
    }).then(() => {
      void client.invalidateQueries({ queryKey: ['tasks'] })
    })
    setTitle('')
    setPriority(2)
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
        <DialogTitle>Add todo</DialogTitle>
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
              Add todo
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
