import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Inbox } from 'lucide-react'
import { AttentionRow } from '@/components/attention/AttentionRow'
import { EmptyState } from '@/components/shared/EmptyState'
import { logAttentionToLedger, webexAttentionFiltered, type AttentionItem } from '@/lib/triage'
import { useToast } from '@/lib/useToast'
import { ATTENTION_QUERY_KEY, markHandled } from '@/lib/webex-handled'

function sectionTitle(kind: string) {
  if (kind === 'mention') return 'Mentions'
  if (kind === 'dm') return 'DMs'
  if (kind === 'reply-to-me') return 'Replies'
  if (kind === 'question') return 'Questions'
  return 'Messages'
}

export function AttentionView({
  items,
  loading,
  error,
  onLog,
  onHandle,
}: {
  items: AttentionItem[]
  loading?: boolean
  error?: string
  onLog: (item: AttentionItem, input: { project: string; action_verb: string; summary: string; body?: string }) => Promise<unknown>
  onHandle: (item: AttentionItem, action: 'completed' | 'ignored') => void
}) {
  const grouped = useMemo(() => {
    return ['mention', 'dm', 'reply-to-me', 'question', 'message'].map((kind) => ({ kind, items: items.filter((item) => item.triage_kind === kind) }))
  }, [items])

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-20 font-semibold text-text-primary">Attention Inbox</h1>
        <p className="mt-1 text-13 text-text-secondary">{items.length} unread mentions, DMs, and unanswered questions need review.</p>
      </div>

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
                  onHandle={(action) => onHandle(item, action)}
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
  const queryClient = useQueryClient()
  const toast = useToast((s) => s.show)
  const attention = useQuery({
    queryKey: ATTENTION_QUERY_KEY,
    queryFn: () => webexAttentionFiltered(30),
    staleTime: 30_000,
  })
  const handle = useMutation({
    mutationFn: async ({ item, action }: { item: AttentionItem; action: 'completed' | 'ignored' }) => {
      return markHandled(item.id, action)
    },
    onMutate: async ({ item }) => {
      await queryClient.cancelQueries({ queryKey: ATTENTION_QUERY_KEY })
      const previous = queryClient.getQueryData<AttentionItem[]>(ATTENTION_QUERY_KEY)
      queryClient.setQueryData<AttentionItem[]>(ATTENTION_QUERY_KEY, (current) =>
        (current ?? []).filter((row) => row.id !== item.id),
      )
      return { previous }
    },
    onSuccess: ({ action }) => {
      toast({ kind: 'success', message: action === 'completed' ? 'Marked done' : 'Ignored' })
    },
    onError: (_error, _variables, context) => {
      queryClient.setQueryData(ATTENTION_QUERY_KEY, context?.previous ?? [])
      toast({ kind: 'error', message: 'Could not update that attention item.' })
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ATTENTION_QUERY_KEY })
    },
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
      toast({ kind: 'success', message: `Logged as [ledger:${result.id}]` })
    },
  })
  return (
    <AttentionView
      items={useMemo(() => attention.data ?? [], [attention.data])}
      loading={attention.isLoading}
      error={attention.isError ? 'Could not load the attention inbox.' : log.isError ? 'Could not log that item to the ledger.' : undefined}
      onLog={(item, input) => log.mutateAsync({ item, input })}
      onHandle={(item, action) => handle.mutate({ item, action })}
    />
  )
}
