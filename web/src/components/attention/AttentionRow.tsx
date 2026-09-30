import { useState } from 'react'
import { ExternalLink, Loader2 } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { AttentionItem } from '@/lib/triage'

function tone(staleness?: number | null) {
  if (staleness == null || staleness < 4) return 'bg-success'
  if (staleness < 24) return 'bg-warning'
  return 'bg-danger'
}

type AttentionRowProps = {
  item: AttentionItem
  onLog: (input: { project: string; action_verb: string; summary: string; body?: string }) => Promise<unknown>
}

export function AttentionRow({ item, onLog }: AttentionRowProps) {
  const [open, setOpen] = useState(false)
  const [project, setProject] = useState('sb')
  const [verb, setVerb] = useState(item.suggested_action_verb || 'Discussed')
  const [summary, setSummary] = useState(item.preview)
  const [saving, setSaving] = useState(false)

  return (
    <div className="flex gap-3 rounded-xl border border-border-subtle bg-bg-panel/92 p-4 transition-colors duration-fast ease-out hover:border-border-strong hover:bg-bg-elevated">
      <div className={`mt-1 w-0.5 shrink-0 rounded-full ${tone(item.staleness_hours)}`} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <div className="text-13 font-medium text-text-primary">{item.sender_name}</div>
          <div className="text-12 text-text-muted">{item.space_name}</div>
          <div className="ml-auto text-12 text-text-muted">{new Date(item.occurred_at).toLocaleString()}</div>
        </div>
        <p className="mt-1 line-clamp-2 text-13 leading-6 text-text-secondary">{item.preview}</p>
      </div>
      <div className="flex shrink-0 items-start gap-2">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button variant="secondary">Log to ledger</Button>
          </PopoverTrigger>
          <PopoverContent side="left" align="start" className="w-[320px] p-4">
            <div className="space-y-3">
              <div>
                <div className="text-13 font-semibold text-text-primary">Log to ledger</div>
                <div className="mt-1 text-12 text-text-muted">Webex ref is added automatically.</div>
              </div>
              <Input value={project} onChange={(event) => setProject(event.target.value)} placeholder="Project" />
              <Input value={verb} onChange={(event) => setVerb(event.target.value)} placeholder="Verb" />
              <Input value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Summary" />
              <div className="flex justify-end">
                <Button
                  variant="primary"
                  disabled={saving || !project || !summary}
                  onClick={async () => {
                    setSaving(true)
                    try {
                      await onLog({ project, action_verb: verb, summary, body: item.preview })
                      setOpen(false)
                    } finally {
                      setSaving(false)
                    }
                  }}
                >
                  {saving ? <Loader2 size={14} className="animate-spin" /> : null}
                  Confirm
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
        {item.deep_link ? (
          <a
            href={item.deep_link}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-md px-2 py-2 text-12 text-text-secondary transition-colors duration-fast ease-out hover:bg-bg-elevated hover:text-text-primary"
          >
            <ExternalLink size={13} />
            Open in Webex
          </a>
        ) : null}
      </div>
    </div>
  )
}
