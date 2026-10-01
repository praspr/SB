import { FormEvent, useState } from 'react'
import { Loader2, Send, Sparkles } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { askSecondBrain } from '@/lib/chat'

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  citations?: string[]
}

const suggestions = [
  'What should I focus on today?',
  'Which assigned JIRAs are blocked?',
  'What changed recently?',
]

export function ChatPanelView({
  messages,
  question,
  pending,
  error,
  onQuestion,
  onSubmit,
  onSuggestion,
}: {
  messages: ChatMessage[]
  question: string
  pending: boolean
  error?: string
  onQuestion: (value: string) => void
  onSubmit: () => void
  onSuggestion: (value: string) => void
}) {
  return (
    <section className="flex min-h-[520px] flex-col rounded-xl border border-border-subtle bg-bg-panel/92">
      <div className="border-b border-border-subtle p-4">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-accent-300" />
          <h2 className="text-16 font-semibold text-text-primary">Ask your second brain</h2>
        </div>
        <p className="mt-1 text-11 text-text-muted">Read-only · grounded in local todos, JIRA, and signals</p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div>
            <p className="text-13 leading-5 text-text-secondary">
              Ask for priorities, blockers, recent changes, or ticket context.
            </p>
            <div className="mt-4 space-y-2">
              {suggestions.map((suggestion) => (
                <button
                  type="button"
                  key={suggestion}
                  onClick={() => onSuggestion(suggestion)}
                  className="block w-full rounded-lg border border-border-subtle bg-black/15 px-3 py-2 text-left text-12 text-text-secondary transition hover:border-border-strong hover:text-text-primary"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                message.role === 'user'
                  ? 'ml-8 rounded-xl bg-accent-500/15 px-3 py-2 text-13 text-text-primary'
                  : 'mr-3 rounded-xl border border-border-subtle bg-black/15 px-3 py-2 text-13 leading-5 text-text-secondary'
              }
            >
              <div className="whitespace-pre-wrap">{message.content}</div>
              {message.citations && message.citations.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-1">
                  {message.citations.map((citation) => (
                    <span key={citation} className="rounded border border-border-subtle px-1.5 py-0.5 text-10 text-text-muted">
                      {citation}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ))
        )}
        {pending ? (
          <div className="flex items-center gap-2 text-12 text-text-muted">
            <Loader2 size={13} className="animate-spin" />
            Looking through local evidence…
          </div>
        ) : null}
        {error ? <p className="text-12 text-danger">{error}</p> : null}
      </div>

      <form
        className="border-t border-border-subtle p-3"
        onSubmit={(event: FormEvent) => {
          event.preventDefault()
          onSubmit()
        }}
      >
        <div className="flex items-end gap-2">
          <textarea
            aria-label="Ask your second brain"
            value={question}
            maxLength={1000}
            rows={2}
            onChange={(event) => onQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                onSubmit()
              }
            }}
            placeholder="Ask about priorities, JIRAs, or recent work…"
            className="min-h-[58px] flex-1 resize-none rounded-lg border border-border-subtle bg-black/20 px-3 py-2 text-13 text-text-primary outline-none placeholder:text-text-muted focus:border-accent-500"
          />
          <button
            type="submit"
            aria-label="Send"
            disabled={pending || !question.trim()}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-500 text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send size={14} />
          </button>
        </div>
      </form>
    </section>
  )
}

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const mutation = useMutation({ mutationFn: askSecondBrain })

  async function submit(nextQuestion = question) {
    const clean = nextQuestion.trim()
    if (!clean || mutation.isPending) return
    setQuestion('')
    setMessages((current) => [...current, { role: 'user', content: clean }])
    try {
      const result = await mutation.mutateAsync(clean)
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: result.answer, citations: result.citations },
      ])
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: error instanceof Error ? error.message : 'Could not reach the local assistant.',
        },
      ])
    }
  }

  return (
    <ChatPanelView
      messages={messages}
      question={question}
      pending={mutation.isPending}
      error={mutation.isError ? 'The assistant could not answer. Try again.' : undefined}
      onQuestion={setQuestion}
      onSubmit={() => void submit()}
      onSuggestion={(suggestion) => void submit(suggestion)}
    />
  )
}
