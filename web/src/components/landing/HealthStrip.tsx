import { Link } from 'react-router-dom'
import { Ticket } from 'lucide-react'
import { StatTile } from '@/components/ui/stat-tile'
import { SyncFreshness } from '@/components/shell/SyncFreshness'
import { SystemClock } from './SystemClock'
import { StorageGauge } from './StorageGauge'
import { ClaudegateUsageRing, CursorUsageRing } from './UsageRing'

/**
 * HealthStrip — the top-of-landing operations band: live clock/date/day,
 * computer storage, AI-tool usage (Claudegate + Cursor), and pending JIRAs.
 * Each widget degrades independently so one failed source never blanks the row.
 * Replaces the global TopBar on the landing route (clock/usage/sync live here).
 */
export function HealthStrip({ jirasPending, now }: { jirasPending: number; now?: Date }) {
  return (
    <section aria-label="System health" className="space-y-3">
      <div className="flex items-center justify-end">
        <SyncFreshness now={now} />
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <SystemClock now={now} />
        <StorageGauge />
        <Link to="/jira" className="focus-ring rounded-lg">
          <StatTile
            label="JIRAs pending"
            value={jirasPending}
            tone={jirasPending > 0 ? 'warning' : 'default'}
            icon={<Ticket size={14} />}
            delta={jirasPending > 0 ? 'open + active' : 'all clear'}
          />
        </Link>
        <ClaudegateUsageRing />
        <CursorUsageRing />
      </div>
    </section>
  )
}
