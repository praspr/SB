import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Inbox } from 'lucide-react'
import { AttentionRow } from '@/components/attention/AttentionRow'
import { EmptyState } from '@/components/shared/EmptyState'
import { logAttentionToLedger, webexAttentionFiltered, type AttentionItem } from '@/lib/triage'

type ToastState = { id: number; label: string } | null

function sectionTitle(kind: string) {
  if (kind === 'mention') return 'Mentions'
  if (kind === 'dm') return 'DMs'
  return 'Questions'
}

export function AttentionView({
  items,
  loading,
  error,
  toast,
  onLog,
}: {
  items: AttentionItem[]
  loading?: boolean
  error?: string
  toast: ToastState
  onLog: (item: AttentionItem, input: { project: string; action_verb: string; summary: string; body?: string }) => Promise<unknown>
}) {
  const grouped = useMemo(() => {
    return ['mention', 'dm', 'question'].map((kind) => ({ kind, items: items.filter((item) => item.triage_kind === kind) }))
  }, [items])

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-20 font-semibold text-text-primary">Attention Inbox</h1>
        <p className="mt-1 text-13 text-text-secondary">{items.length} unread mentions, DMs, and unanswered questions need review.</p>
      </div>

      {toast ? (
        <div className="rounded-md border border-success/40 bg-success/10 p-3 text-13 text-success">Logged as [ledger:{toast.id}]</div>
      ) : null}

      {error ? <div className="rounded-md border border-danger/40 bg-danger/5 p-3 text-13 text-danger">{error}</div> : null}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-24 animate-pulse rounded-xl border border-border-subtle bg-bg-panel" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="Inbox zero" body="Nothing needs your attention right now." icon={<Inbox size={18} />} />
      ) : (
        <div className="space-y-6">
          {grouped.map((group) => group.items.length > 0 ? (
            <section key={group.kind} className="space-y-3">
              <div className="text-12 uppercase tracking-[0.18em] text-text-muted">{sectionTitle(group.kind)}</div>
              {group.items.map((item) => (
                <AttentionRow
                  key={item.id}
                  item={item}
                  onLog={(input) => onLog(item, input)}
                />
              ))}
            </section>
          ) : null)}
        </div>
      )}
    </div>
  )
}

export function AttentionPage() {
  const [toast, setToast] = useState<ToastState>(null)
  const attention = useQuery({
    queryKey: ['triage', 'attention'],
    queryFn: () => webexAttentionFiltered(30),
    staleTime: 30_000,
  })
  const log = useMutation({
    mutationFn: async ({ item, input }: { item: AttentionItem; input: { project: string; action_verb: string; summary: string; body?: string } }) => {
      return logAttentionToLedger({
        project: input.project,
        action_verb: input.action_verb,
        summary: input.summary,
        body: input.body,
        refs: [
          {
            kind: 'webex',
            value: item.id,
            url: item.deep_link || undefined,
            label: item.space_name,
          },
        ],
        source_harness: 'web',
      })
    },
    onSuccess: (result) => {
      setToast({ id: result.id, label: `ledger:${result.id}` })
      setTimeout(() => setToast(null), 2500)
    },
  })

  return (
    <AttentionView
      items={attention.data ?? []}
      loading={attention.isLoading}
      error={attention.isError ? 'Could not load the attention inbox.' : log.isError ? 'Could not log that item to the ledger.' : undefined}
      toast={toast}
      onLog={(item, input) => log.mutateAsync({ item, input })}
    />
  )
}
