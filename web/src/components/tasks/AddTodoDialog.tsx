import { useState } from 'react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useAddTask } from '@/lib/queries'
import { useUiStore } from '@/lib/store'
import type { Priority, Task } from '@/lib/mock-data'

export function AddTodoDialog() {
  const open = useUiStore((s) => s.addTodoOpen)
  const setOpen = useUiStore((s) => s.setAddTodoOpen)
  const addTask = useAddTask()
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState<Priority>(2)
  const [domain, setDomain] = useState<Task['domain']>('work')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    addTask.mutate({ title: title.trim(), priority, domain })
    setTitle('')
    setPriority(2)
    setDomain('work')
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
