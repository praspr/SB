import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./mcp', () => ({
  callTool: vi.fn(),
}))

describe('webex queries', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('maps mirrored meetings and keeps join links', async () => {
    const { callTool } = await import('./mcp')
    vi.mocked(callTool).mockResolvedValue([
      {
        id: 'm1',
        title: 'Standup',
        start: '2026-09-30T15:00:00Z',
        end: '2026-09-30T15:30:00Z',
        join_url: 'https://webex.example/join/m1',
        attendees: [{ name: 'Ada', email: 'ada@example.com' }],
      },
    ])
    const { listMeetings } = await import('./queries')
    const meetings = await listMeetings()
    expect(callTool).toHaveBeenCalledWith('list_webex_meetings')
    expect(meetings[0].join_url).toBe('https://webex.example/join/m1')
    expect(meetings[0].attendees[0].name).toBe('Ada')
  })

  it('maps mention previews without requiring a full message body', async () => {
    const { toWebexMessage } = await import('./queries')
    const message = toWebexMessage({
      id: 'msg1',
      space_id: 's1',
      space_name: 'Team',
      sender_name: 'Ada',
      sender_email: 'ada@example.com',
      is_dm: 0,
      is_mention: 1,
      is_unread: 1,
      preview: 'Can you review?',
      occurred_at: '2026-09-30T14:00:00Z',
      deep_link: 'https://webex.example/msg1',
    })
    expect(message.is_mention).toBe(true)
    expect(message.preview).toBe('Can you review?')
    expect(message.url).toBe('https://webex.example/msg1')
  })
})
