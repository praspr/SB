import { useMemo, useState } from 'react'
import { Copy, FilePlus2, Link2, Mail } from 'lucide-react'
import type { LedgerEntry } from '@/lib/ledger'
import type { ReportResult } from '@/lib/reports'
import { Button } from '@/components/ui/button'
import { buildMailto, WebexPostButton } from '@/components/reports/WebexPostButton'
import { useToast } from '@/lib/useToast'

type ReportViewerProps = {
  report?: ReportResult | null
  entries?: LedgerEntry[]
  loading?: boolean
  error?: string
  canSave?: boolean
  savePending?: boolean
  template?: string
  date?: string
  onCopy?: () => void
  onSave?: () => void
}

type CitationPart = { type: 'text'; value: string } | { type: 'citation'; value: number }

function parseParts(text: string): CitationPart[] {
  const parts: CitationPart[] = []
  const regex = /\[ledger:(\d+)\]/g
  let lastIndex = 0

  for (const match of text.matchAll(regex)) {
    const index = match.index ?? 0
    if (index > lastIndex) parts.push({ type: 'text', value: text.slice(lastIndex, index) })
    parts.push({ type: 'citation', value: Number(match[1]) })
    lastIndex = index + match[0].length
  }

  if (lastIndex < text.length) parts.push({ type: 'text', value: text.slice(lastIndex) })
  return parts.length ? parts : [{ type: 'text', value: text }]
}

function MarkdownLine({
  line,
  onCitation,
}: {
  line: string
  onCitation: (id: number) => void
}) {
  const parts = parseParts(line.replace(/^[-*]\s+/, ''))
  const content = parts.map((part, index) =>
    part.type === 'text' ? (
      <span key={`${part.value}-${index}`}>{part.value}</span>
    ) : (
      <button
        key={part.value}
        type="button"
        onClick={() => onCitation(part.value)}
        className="mx-0.5 inline-flex items-center rounded border border-border-subtle px-1.5 py-0.5 text-12 text-text-secondary transition-colors duration-fast ease-out hover:border-border-strong hover:text-text-primary"
      >
        [ledger:{part.value}]
      </button>
    )
  )

  if (line.startsWith('# ')) return <h2 className="text-20 font-semibold text-text-primary">{line.slice(2)}</h2>
  if (line.startsWith('## ')) return <h3 className="text-16 font-semibold text-text-primary">{line.slice(3)}</h3>
  if (line.startsWith('### ')) return <h4 className="text-14 font-semibold text-text-primary">{line.slice(4)}</h4>
  if (line.startsWith('- ')) return <li className="ml-4 list-disc text-13 leading-6 text-text-secondary">{content}</li>
  if (!line.trim()) return <div className="h-2" />
  return <p className="text-13 leading-6 text-text-secondary">{content}</p>
}

export function ReportViewer({
  report,
  entries = [],
  loading,
  error,
  canSave,
  savePending,
  template,
  date,
  onCopy,
  onSave,
}: ReportViewerProps) {
  const [selectedCitation, setSelectedCitation] = useState<number | null>(null)
  const showToast = useToast((s) => s.show)

  const citedEntries = useMemo(() => {
    const byId = new Map(entries.map((entry) => [entry.id, entry]))
    return (report?.citations ?? []).map((id) => byId.get(id)).filter(Boolean) as LedgerEntry[]
  }, [entries, report?.citations])

  if (loading) {
    return <div className="rounded-xl border border-border-subtle bg-bg-panel/92 p-6 text-13 text-text-muted">Running report…</div>
  }

  if (error) {
    return <div className="rounded-xl border border-danger/40 bg-danger/5 p-4 text-13 text-danger">{error}</div>
  }

  if (!report) {
    return (
      <div className="rounded-xl border border-dashed border-border-subtle bg-bg-panel/60 p-8 text-center text-13 text-text-muted">
        Pick a template and hit Run.
      </div>
    )
  }

  const selectedEntry = selectedCitation ? citedEntries.find((entry) => entry.id === selectedCitation) : citedEntries[0]
  const lines = report.markdown.split('\n')

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
      <section className="rounded-xl border border-border-subtle bg-bg-panel/92 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-4">
          <div>
            <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Report</div>
            <div className="mt-1 text-13 text-text-secondary">Markdown output with local ledger citations.</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={onCopy}>
              <Copy size={14} />
              Copy markdown
            </Button>
            <Button variant="secondary" onClick={onSave} disabled={!canSave || savePending}>
              <FilePlus2 size={14} />
              {savePending ? 'Saving note' : 'Save as ledger note'}
            </Button>
            <WebexPostButton markdown={report.markdown} />
            {template === 'wrap' && (
              <Button
                variant="secondary"
                onClick={() => {
                  showToast({ kind: 'info', message: 'Opened email draft.' })
                  window.location.href = buildMailto(date || new Date().toISOString().slice(0, 10), report.markdown)
                }}
              >
                <Mail size={14} />
                Email draft
              </Button>
            )}
          </div>
        </div>

        <div className="mt-5 space-y-1">
          {lines.map((line, index) => (
            <MarkdownLine key={`${index}-${line}`} line={line} onCitation={setSelectedCitation} />
          ))}
        </div>
      </section>

      <aside className="rounded-xl border border-border-subtle bg-bg-panel/92 p-4">
        <div className="flex items-center gap-2">
          <Link2 size={14} className="text-text-muted" />
          <h3 className="text-14 font-semibold text-text-primary">Referenced ledger entries</h3>
        </div>
        {!citedEntries.length ? (
          <p className="mt-4 text-13 text-text-muted">No citations were returned for this report run.</p>
        ) : (
          <div className="mt-4 space-y-3">
            <div className="space-y-2">
              {citedEntries.map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => setSelectedCitation(entry.id)}
                  className={`w-full rounded-lg border px-3 py-2 text-left transition-colors duration-fast ease-out ${selectedCitation === entry.id || (!selectedCitation && selectedEntry?.id === entry.id)
                    ? 'border-border-strong bg-bg-elevated'
                    : 'border-border-subtle bg-black/20 hover:border-border-strong hover:bg-bg-elevated'
                  }`}
                >
                  <div className="text-12 text-text-muted">ledger:{entry.id}</div>
                  <div className="mt-1 text-13 text-text-primary">{entry.summary}</div>
                </button>
              ))}
            </div>

            {selectedEntry && (
              <div className="rounded-lg border border-border-subtle bg-black/20 p-3">
                <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Selected entry</div>
                <div className="mt-2 text-13 font-medium text-text-primary">{selectedEntry.action_verb} · {selectedEntry.project}</div>
                <div className="mt-1 text-12 text-text-muted">{selectedEntry.ts}</div>
                <p className="mt-3 text-13 leading-6 text-text-secondary">{selectedEntry.body || selectedEntry.summary}</p>
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  )
}
