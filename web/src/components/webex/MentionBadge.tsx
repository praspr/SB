import { AtSign } from 'lucide-react'

export function MentionBadge() {
  return (
    <span className="flex items-center gap-1 rounded-full border border-accent-700 bg-accent-800/40 px-2 py-0.5 text-[11px] font-medium text-accent-200">
      <AtSign size={10} /> mention
    </span>
  )
}
