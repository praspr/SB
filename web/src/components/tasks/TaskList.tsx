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
  goalTitles = {},
}: {
  tasks: Task[] | undefined
  isLoading?: boolean
  emptyTitle?: string
  emptyBody?: string
  goalTitles?: Record<number, string>
}) {
  if (isLoading) return <SkeletonRow lines={5} />
  if (!tasks || tasks.length === 0) {
    return <EmptyState title={emptyTitle} body={emptyBody} />
  }

  return (
    <motion.div
      className="space-y-2"
      initial="hidden"
      animate="show"
      variants={{ show: { transition: { staggerChildren: 0.03 } } }}
    >
      {tasks.map((task) => (
        <motion.div
          key={task.id}
          layout
          variants={{ hidden: { opacity: 0, y: 6 }, show: { opacity: 1, y: 0 } }}
        >
          <TaskRow task={task} goalTitle={task.goal_id ? goalTitles[task.goal_id] : undefined} />
        </motion.div>
      ))}
    </motion.div>
  )
}
