import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { ScheduledRitual } from '@/lib/schedules'

export const RITUAL_OPTIONS = [
  'wrap_day',
  'standup',
  'plan_day',
  'report_daily',
  'report_weekly',
  'report_monthly',
  'sync_jira',
  'sync_webex',
]

type SchedulesTabProps = {
  schedules: ScheduledRitual[]
  name: string
  onName: (value: string) => void
  ritual: string
  onRitual: (value: string) => void
  cron: string
  onCron: (value: string) => void
  enabled: boolean
  onEnabled: (value: boolean) => void
  onAdd: () => void
  onDelete: (id: number) => void
  addPending?: boolean
  removePending?: boolean
}

/** Pure presentational schedules tab body -- kept separate from
 * SettingsPopover so it can be rendered and asserted on directly in tests
 * without needing to open the Radix popover/tabs first. */
export function SchedulesTab({
  schedules,
  name,
  onName,
  ritual,
  onRitual,
  cron,
  onCron,
  enabled,
  onEnabled,
  onAdd,
  onDelete,
  addPending,
  removePending,
}: SchedulesTabProps) {
  return (
    <div className="space-y-3">
      <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Schedules</div>
      <div className="space-y-2">
        {schedules.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border-subtle bg-black/10 p-3 text-12 text-text-muted">
            No scheduled rituals yet.
          </div>
        ) : (
          schedules.map((schedule) => (
            <div key={schedule.id} className="rounded-lg border border-border-subtle bg-black/20 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-13 font-medium text-text-primary">{schedule.name}</div>
                  <div className="mt-1 text-12 text-text-muted">
                    {schedule.ritual} · <code>{schedule.cron}</code>
                  </div>
                  <div className="mt-1 text-12 text-text-muted">
                    {schedule.enabled ? 'enabled' : 'disabled'}
                    {schedule.last_run_at ? ` · last run ${schedule.last_run_at}` : ''}
                    {schedule.last_status ? ` · ${schedule.last_status}` : ''}
                  </div>
                </div>
                <button
                  type="button"
                  aria-label={`Delete schedule ${schedule.name}`}
                  onClick={() => onDelete(schedule.id)}
                  disabled={removePending}
                  className="shrink-0 rounded-md border border-border-subtle p-1.5 text-text-muted transition-colors duration-fast ease-out hover:border-danger/60 hover:text-danger"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="rounded-lg border border-border-subtle bg-black/20 p-3">
        <div className="text-13 font-medium text-text-primary">Add schedule</div>
        <div className="mt-3 space-y-2">
          <Input value={name} onChange={(event) => onName(event.target.value)} placeholder="Name (e.g. Friday wrap)" />
          <select
            value={ritual}
            onChange={(event) => onRitual(event.target.value)}
            className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-3 text-13 text-text-primary outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500"
          >
            {RITUAL_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <Input value={cron} onChange={(event) => onCron(event.target.value)} placeholder="Cron (e.g. 0 16 * * 5)" />
          <label className="flex items-center gap-2 text-12 text-text-secondary">
            <input type="checkbox" checked={enabled} onChange={(event) => onEnabled(event.target.checked)} />
            Enabled
          </label>
          <Button variant="secondary" disabled={!name || !cron || addPending} onClick={onAdd}>
            {addPending ? 'Adding' : 'Add schedule'}
          </Button>
        </div>
        <div className="mt-2 text-12 text-text-muted">
          Schedules run every 5 minutes inside the local sb-core service.
        </div>
      </div>
    </div>
  )
}
