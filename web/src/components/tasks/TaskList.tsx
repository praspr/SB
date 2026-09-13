import { motion } from 'framer-motion'
import type { Task } from '@/lib/mock-data'
import { TaskRow } from './TaskRow'
import { EmptyState } from '@/components/shared/EmptyState'
import { SkeletonRow } from '@/components/shared/SkeletonRow'

export function TaskList({
  tasks,
  isLoading,
  emptyTitle = 'No tasks',
  emptyBody = 'Nothing here yet. Add a todo to get started.',
}: {
  tasks: Task[] | undefined
  isLoading?: boolean
  emptyTitle?: string
  emptyBody?: string
}) {
  if (isLoading) return <SkeletonRow lines={5} />
  if (!tasks || tasks.length === 0) {
    return <EmptyState title={emptyTitle} body={emptyBody} />
  }

  return (
    <div className="space-y-2">
      {tasks.map((task) => (
        <motion.div key={task.id} layout>
          <TaskRow task={task} />
        </motion.div>
      ))}
    </div>
  )
}
