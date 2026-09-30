import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ledgerLog, ledgerProjects, type LedgerRef } from '@/lib/ledger'

type AttachRefDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  ref: LedgerRef
}

/** Small dialog to capture a one-line summary and attach a pre-filled ref
 * (a GitHub PR link, a file:// URI, or a generic URL) as a ledger note. */
export function AttachRefDialog({ open, onOpenChange, ref: attachedRef }: AttachRefDialogProps) {
  const [project, setProject] = useState('')
  const [summary, setSummary] = useState('')

  const projects = useQuery({ queryKey: ['ledger', 'projects'], queryFn: ledgerProjects, enabled: open, staleTime: 30_000 })

  const attach = useMutation({
    mutationFn: () =>
      ledgerLog({
        project,
        summary: summary || attachedRef.value,
        action_verb: 'Noted',
        refs: [attachedRef],
        source_harness: 'web',
      }),
    onSuccess: () => {
      onOpenChange(false)
      setSummary('')
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitle>Attach as ledger ref</DialogTitle>
        <div className="mt-4 space-y-3">
          <div className="rounded-md border border-border-subtle bg-black/20 px-3 py-2 text-12 text-text-muted">
            {attachedRef.kind}: {attachedRef.value}
          </div>
          <label className="block space-y-1.5">
            <span className="text-12 text-text-muted">Project</span>
            <select
              value={project}
              onChange={(event) => setProject(event.target.value)}
              className="h-9 w-full rounded-md border border-border-subtle bg-bg-panel px-3 text-13 text-text-primary outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500"
            >
              <option value="">Select a project</option>
              {(projects.data ?? []).map((item) => (
                <option key={item.project} value={item.project}>
                  {item.project}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1.5">
            <span className="text-12 text-text-muted">Summary</span>
            <Input
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="What is this reference about?"
            />
          </label>
          <Button
            variant="primary"
            disabled={!project || attach.isPending}
            onClick={() => attach.mutate()}
          >
            {attach.isPending ? 'Saving' : 'Attach to ledger'}
          </Button>
          {attach.isError && <div className="text-12 text-danger">Could not save this note.</div>}
        </div>
      </DialogContent>
    </Dialog>
  )
}
