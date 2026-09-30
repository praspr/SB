import type { LedgerEntry } from '@/lib/ledger'

export function LedgerTable({
  entries,
  onSelect,
}: {
  entries: LedgerEntry[]
  onSelect: (entry: LedgerEntry) => void
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-border-subtle bg-bg-panel/92">
      <table className="w-full border-collapse text-left text-13">
        <thead className="border-b border-border-subtle bg-black/20 text-text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">ts</th>
            <th className="px-3 py-2 font-medium">project</th>
            <th className="px-3 py-2 font-medium">verb</th>
            <th className="px-3 py-2 font-medium">summary</th>
            <th className="px-3 py-2 font-medium">refs</th>
            <th className="px-3 py-2 font-medium">source</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr
              key={entry.id}
              className="cursor-pointer border-b border-border-subtle/70 text-text-secondary transition-colors duration-fast ease-out hover:bg-bg-elevated"
              onClick={() => onSelect(entry)}
            >
              <td className="px-3 py-2 text-text-muted">{entry.ts.replace('T', ' ').replace('Z', '')}</td>
              <td className="px-3 py-2 text-text-primary">{entry.project}</td>
              <td className="px-3 py-2">{entry.action_verb}</td>
              <td className="px-3 py-2 text-text-primary">{entry.summary}</td>
              <td className="px-3 py-2 text-text-muted">{entry.refs.length}</td>
              <td className="px-3 py-2 text-text-muted">{entry.source_harness}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
