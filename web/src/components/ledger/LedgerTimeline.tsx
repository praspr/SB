import type { LedgerEntry } from '@/lib/ledger'

function groupByDay(entries: LedgerEntry[]) {
  const groups = new Map<string, LedgerEntry[]>()
  entries.forEach((entry) => {
    const day = entry.ts.slice(0, 10)
    if (!groups.has(day)) groups.set(day, [])
    groups.get(day)!.push(entry)
  })
  return Array.from(groups.entries())
}

export function LedgerTimeline({
  entries,
  onSelect,
}: {
  entries: LedgerEntry[]
  onSelect: (entry: LedgerEntry) => void
}) {
  const groups = groupByDay(entries)

  return (
    <div className="space-y-6">
      {groups.map(([day, dayEntries]) => (
        <section key={day}>
          <div className="mb-3 text-14 font-semibold text-text-primary">{day}</div>
          <div className="space-y-3 border-l border-border-subtle pl-4">
            {dayEntries.map((entry) => (
              <button
                key={entry.id}
                type="button"
                onClick={() => onSelect(entry)}
                className="group relative block w-full rounded-xl border border-border-subtle bg-bg-panel/92 p-4 text-left transition-colors duration-fast ease-out hover:border-border-strong hover:bg-bg-elevated"
              >
                <span className="absolute -left-[21px] top-5 h-2.5 w-2.5 rounded-full border border-border-strong bg-bg-panel" />
                <div className="flex flex-wrap items-center gap-2 text-12 text-text-muted">
                  <span>{entry.ts.slice(11, 16)}</span>
                  <span>·</span>
                  <span>{entry.project}</span>
                  <span>·</span>
                  <span>{entry.source_harness}</span>
                </div>
                <div className="mt-2 flex items-start justify-between gap-3">
                  <div>
                    <div className="text-13 font-medium text-text-primary">{entry.action_verb}</div>
                    <p className="mt-1 text-13 leading-6 text-text-secondary group-hover:text-text-primary">{entry.summary}</p>
                  </div>
                  <span className="rounded-full border border-border-subtle bg-black/20 px-2 py-0.5 text-12 text-text-muted">
                    {entry.refs.length} refs
                  </span>
                </div>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
