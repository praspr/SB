import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Send } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { listWebexSpaces, webexPostMessage, type WebexSpaceOption } from '@/lib/webex-post'

const MAILTO_MAX_BODY_CHARS = 8000
const TRUNCATION_SUFFIX = '\u2026\n\n(truncated \u2014 see dashboard for full content)'

/** Pure: build a mailto: URL for a daily-wrap email draft, truncating a long body. */
export function buildMailto(date: string, markdown: string): string {
  const truncated = markdown.length > MAILTO_MAX_BODY_CHARS
  const body = truncated ? markdown.slice(0, MAILTO_MAX_BODY_CHARS) + TRUNCATION_SUFFIX : markdown
  const subject = `Daily wrap ${date}`
  return `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

type WebexPostPopoverBodyProps = {
  spaces: WebexSpaceOption[]
  spaceId: string
  onSpaceIdChange: (value: string) => void
  onPost: () => void
  posting?: boolean
  error?: string
  successLabel?: string
}

/** Pure presentational popover body -- kept separate from WebexPostButton so it
 * can be rendered and asserted on directly in tests without simulating a
 * Radix popover open interaction. */
export function WebexPostPopoverBody({
  spaces,
  spaceId,
  onSpaceIdChange,
  onPost,
  posting,
  error,
  successLabel,
}: WebexPostPopoverBodyProps) {
  return (
    <div className="w-72 space-y-3">
      <div className="text-12 uppercase tracking-[0.18em] text-text-muted">Post to Webex</div>
      <label className="block space-y-1.5">
        <span className="text-12 text-text-muted">Space</span>
        <Input
          list="webex-post-space-options"
          value={spaceId}
          onChange={(event) => onSpaceIdChange(event.target.value)}
          placeholder="Search spaces..."
        />
        <datalist id="webex-post-space-options">
          {spaces.map((space) => (
            <option key={space.id} value={space.id}>
              {space.name}
            </option>
          ))}
        </datalist>
      </label>
      <Button variant="primary" onClick={onPost} disabled={!spaceId || posting}>
        <Send size={14} />
        {posting ? 'Posting' : 'Post'}
      </Button>
      {error && <div className="text-12 text-danger">{error}</div>}
      {successLabel && <div className="text-12 text-success">{successLabel}</div>}
    </div>
  )
}

export function WebexPostButton({ markdown }: { markdown: string }) {
  const [open, setOpen] = useState(false)
  const [spaceId, setSpaceId] = useState('')
  const [successLabel, setSuccessLabel] = useState<string>()
  const [error, setError] = useState<string>()

  const spacesQuery = useQuery({
    queryKey: ['webex-post', 'spaces'],
    queryFn: listWebexSpaces,
    enabled: open,
    staleTime: 30_000,
  })

  const post = useMutation({
    mutationFn: () => webexPostMessage(spaceId, markdown),
    onSuccess: (result) => {
      if (result.posted) {
        const space = (spacesQuery.data ?? []).find((s) => s.id === spaceId)
        setError(undefined)
        setSuccessLabel(`Posted to ${space?.name || spaceId}`)
      } else {
        setSuccessLabel(undefined)
        setError(result.error || 'Could not post to Webex.')
      }
    },
    onError: (err: Error) => {
      setSuccessLabel(undefined)
      setError(err.message || 'Could not post to Webex.')
    },
  })

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="secondary">
          <Send size={14} />
          Post to Webex
        </Button>
      </PopoverTrigger>
      <PopoverContent side="bottom" align="end">
        <WebexPostPopoverBody
          spaces={spacesQuery.data ?? []}
          spaceId={spaceId}
          onSpaceIdChange={setSpaceId}
          onPost={() => post.mutate()}
          posting={post.isPending}
          error={error}
          successLabel={successLabel}
        />
      </PopoverContent>
    </Popover>
  )
}
