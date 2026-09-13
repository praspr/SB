import { CheckCircle2 } from 'lucide-react'
import { useTodayTasks, useTodayMeetings } from '@/lib/queries'
import { TaskList } from '@/components/tasks/TaskList'
import { MeetingList } from '@/components/meetings/MeetingList'
import { UsageStats } from '@/components/landing/UsageStats'

export function LandingPage() {
  const { data: tasks, isLoading: tasksLoading } = useTodayTasks()
  const { data: meetings, isLoading: meetingsLoading } = useTodayMeetings()

  return (
    <div className="space-y-6">
      <div>
        <h2 className="mb-2 text-xs uppercase tracking-wide text-neutral-500">Usage</h2>
        <UsageStats />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Must-do</div>
              <h2 className="mt-1 text-16 font-semibold text-text-primary">Today's todos</h2>
            </div>
            <span className="flex items-center gap-1.5 rounded-full border border-border-subtle bg-black/20 px-2.5 py-1 text-12 text-text-secondary">
              <CheckCircle2 size={12} />
              {tasks?.length ?? 0}
            </span>
          </div>
          <div className="mt-4">
            <TaskList
              tasks={tasks}
              isLoading={tasksLoading}
              emptyTitle="You're all caught up"
              emptyBody="No must-do tasks for today. Add one to get started."
            />
          </div>
        </section>

        <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Calendar</div>
              <h2 className="mt-1 text-16 font-semibold text-text-primary">Meetings today</h2>
            </div>
            <span className="rounded-full border border-border-subtle bg-black/20 px-2.5 py-1 text-12 tabular text-text-secondary">
              {meetings?.length ?? 0}
            </span>
          </div>
          <div className="mt-4">
            <MeetingList meetings={meetings} isLoading={meetingsLoading} emptyBody="Nothing on today's calendar." />
          </div>
        </section>
      </div>
    </div>
  )
}
