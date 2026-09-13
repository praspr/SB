import { forwardRef, useImperativeHandle, useRef, useState } from 'react'
import { Plus } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { useAddTask } from '@/lib/queries'

export type QuickAddInputHandle = {
  focus: () => void
}

export const QuickAddInput = forwardRef<QuickAddInputHandle>(function QuickAddInput(_props, ref) {
  const [title, setTitle] = useState('')
  const addTask = useAddTask()
  const inputRef = useRef<HTMLInputElement>(null)

  useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
  }))

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    addTask.mutate({ title: title.trim(), priority: 2, domain: 'work' })
    setTitle('')
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-panel px-3 py-1.5">
      <Plus size={16} className="shrink-0 text-text-muted" />
      <Input
        ref={inputRef}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Add a todo and press Enter…"
        className="h-8 border-none bg-transparent px-0 focus:ring-0"
      />
    </form>
  )
})
