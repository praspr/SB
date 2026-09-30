import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { Goal, GoalStatus, GoalTier } from '@/lib/goals'

export function GoalDialog({
  open,
  goal,
  onOpenChange,
  onSubmit,
}: {
  open: boolean
  goal?: Goal | null
  onOpenChange: (open: boolean) => void
  onSubmit: (input: {
    id?: number
    tier: GoalTier
    title: string
    description?: string
    keywords: string[]
    target_date?: string
    status?: GoalStatus
  }) => void
}) {
  const [tier, setTier] = useState<GoalTier>('weekly')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [keywords, setKeywords] = useState('')
  const [targetDate, setTargetDate] = useState('')
  const [status, setStatus] = useState<GoalStatus>('active')

  useEffect(() => {
    if (!goal) {
      setTier('weekly')
      setTitle('')
      setDescription('')
      setKeywords('')
      setTargetDate('')
      setStatus('active')
      return
    }
    setTier(goal.tier)
    setTitle(goal.title)
    setDescription(goal.description || '')
    setKeywords(goal.keywords.join(', '))
    setTargetDate(goal.target_date || '')
    setStatus(goal.status)
  }, [goal])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitle>{goal ? 'Edit goal' : 'New goal'}</DialogTitle>
        <form
          className="mt-4 space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (!title.trim()) return
            onSubmit({
              id: goal?.id,
              tier,
              title: title.trim(),
              description: description.trim() || undefined,
              keywords: keywords.split(',').map((keyword) => keyword.trim()).filter(Boolean),
              target_date: targetDate || undefined,
              status,
            })
          }}
        >
          <div className="grid grid-cols-2 gap-3">
            <label>
              <div className="mb-1 text-12 text-text-secondary">Tier</div>
              <select value={tier} onChange={(event) => setTier(event.target.value as GoalTier)} className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-2 text-13 text-text-primary outline-none focus:border-accent-500">
                <option value="contractual">Contractual</option>
                <option value="quarterly">Quarterly</option>
                <option value="weekly">Weekly</option>
              </select>
            </label>
            <label>
              <div className="mb-1 text-12 text-text-secondary">Status</div>
              <select value={status} onChange={(event) => setStatus(event.target.value as GoalStatus)} className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-2 text-13 text-text-primary outline-none focus:border-accent-500">
                <option value="active">Active</option>
                <option value="done">Done</option>
                <option value="archived">Archived</option>
              </select>
            </label>
          </div>
          <label>
            <div className="mb-1 text-12 text-text-secondary">Title</div>
            <Input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            <div className="mb-1 text-12 text-text-secondary">Description</div>
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} className="min-h-[88px] w-full rounded-md border border-border-subtle bg-bg-panel px-3 py-2 text-13 text-text-primary outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label>
              <div className="mb-1 text-12 text-text-secondary">Keywords</div>
              <Input value={keywords} onChange={(event) => setKeywords(event.target.value)} placeholder="release, automation" />
            </label>
            <label>
              <div className="mb-1 text-12 text-text-secondary">Target date</div>
              <Input type="date" value={targetDate} onChange={(event) => setTargetDate(event.target.value)} />
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" variant="primary">Save goal</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
