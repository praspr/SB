import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

type CallTool = typeof import('./mcp')['callTool']

function initializeResponse(session = 'session-123') {
  return Response.json(
    {
      jsonrpc: '2.0',
      id: 1,
      result: {
        protocolVersion: '2025-06-18',
        capabilities: {},
        serverInfo: { name: 'sb', version: '1' },
      },
    },
    { headers: { 'Mcp-Session-Id': session } },
  )
}

function toolResponse<T>(value: T) {
  return Response.json({
    jsonrpc: '2.0',
    id: 2,
    result: {
      structuredContent: { result: value },
      content: [{ type: 'text', text: JSON.stringify(value) }],
    },
  })
}

async function loadCallTool(): Promise<CallTool> {
  return (await import('./mcp')).callTool
}

describe('callTool', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('initializes once, propagates the session, and extracts a tool result', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(initializeResponse())
      .mockResolvedValueOnce(new Response(null, { status: 202 }))
      .mockResolvedValueOnce(toolResponse([{ id: 7, title: 'Ship MCP cutover' }]))
    vi.stubGlobal('fetch', fetchMock)
    const callTool = await loadCallTool()

    const result = await callTool<Array<{ id: number; title: string }>>('todo_list', {
      status: 'all',
    })

    expect(result).toEqual([{ id: 7, title: 'Ship MCP cutover' }])
    expect(fetchMock).toHaveBeenCalledTimes(3)

    const requests = fetchMock.mock.calls.map(([, init]) => ({
      body: JSON.parse(String(init?.body)),
      headers: new Headers(init?.headers),
    }))
    expect(requests.map(({ body }) => body.method)).toEqual([
      'initialize',
      'notifications/initialized',
      'tools/call',
    ])
    expect(requests[0].body.id).toBe(1)
    expect(requests[1].body.id).toBeUndefined()
    expect(requests[2].body).toMatchObject({
      id: 2,
      params: { name: 'todo_list', arguments: { status: 'all' } },
    })
    expect(requests[0].headers.has('Mcp-Session-Id')).toBe(false)
    expect(requests[1].headers.get('Mcp-Session-Id')).toBe('session-123')
    expect(requests[2].headers.get('Mcp-Session-Id')).toBe('session-123')
  })

  it('retries initialization after an initialize failure', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response('unavailable', { status: 503 }))
      .mockResolvedValueOnce(initializeResponse('session-retry'))
      .mockResolvedValueOnce(new Response(null, { status: 202 }))
      .mockResolvedValueOnce(toolResponse(['recovered']))
    vi.stubGlobal('fetch', fetchMock)
    const callTool = await loadCallTool()

    await expect(callTool('todo_list')).rejects.toThrow('MCP HTTP 503')
    await expect(callTool<string[]>('todo_list')).resolves.toEqual(['recovered'])

    const methods = fetchMock.mock.calls.map(([, init]) => JSON.parse(String(init?.body)).method)
    expect(methods).toEqual([
      'initialize',
      'initialize',
      'notifications/initialized',
      'tools/call',
    ])
  })

  it('clears a stale session after a tools/call 404 so the next call reinitializes', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(initializeResponse('session-stale'))
      .mockResolvedValueOnce(new Response(null, { status: 202 }))
      .mockResolvedValueOnce(new Response('session not found', { status: 404 }))
      .mockResolvedValueOnce(initializeResponse('session-new'))
      .mockResolvedValueOnce(new Response(null, { status: 202 }))
      .mockResolvedValueOnce(toolResponse(['recovered']))
    vi.stubGlobal('fetch', fetchMock)
    const callTool = await loadCallTool()

    await expect(callTool('todo_list')).rejects.toThrow('MCP HTTP 404')
    await expect(callTool<string[]>('todo_list')).resolves.toEqual(['recovered'])

    const requests = fetchMock.mock.calls.map(([, init]) => ({
      body: JSON.parse(String(init?.body)),
      headers: new Headers(init?.headers),
    }))
    expect(requests.map(({ body }) => body.method)).toEqual([
      'initialize',
      'notifications/initialized',
      'tools/call',
      'initialize',
      'notifications/initialized',
      'tools/call',
    ])
    expect(requests[2].headers.get('Mcp-Session-Id')).toBe('session-stale')
    expect(requests[3].headers.has('Mcp-Session-Id')).toBe(false)
    expect(requests[5].headers.get('Mcp-Session-Id')).toBe('session-new')
  })

  it('extracts a tools/call result from the first complete SSE event', async () => {
    const encoder = new TextEncoder()
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            'event: message\ndata: {"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"[1,2,3]"}]}}\n\n',
          ),
        )
      },
    })
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(initializeResponse())
      .mockResolvedValueOnce(new Response(null, { status: 202 }))
      .mockResolvedValueOnce(
        new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const callTool = await loadCallTool()

    await expect(
      Promise.race([
        callTool<number[]>('todo_list'),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('SSE parser buffered the open stream')), 100),
        ),
      ]),
    ).resolves.toEqual([1, 2, 3])
  })

  it('shares one initialization across concurrent tool calls', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(initializeResponse())
      .mockResolvedValueOnce(new Response(null, { status: 202 }))
      .mockResolvedValueOnce(toolResponse(['first']))
      .mockResolvedValueOnce(toolResponse(['second']))
    vi.stubGlobal('fetch', fetchMock)
    const callTool = await loadCallTool()

    await expect(
      Promise.all([callTool<string[]>('todo_list'), callTool<string[]>('jira_status')]),
    ).resolves.toEqual([['first'], ['second']])

    const methods = fetchMock.mock.calls.map(([, init]) => JSON.parse(String(init?.body)).method)
    expect(methods.filter((method) => method === 'initialize')).toHaveLength(1)
    expect(methods).toEqual([
      'initialize',
      'notifications/initialized',
      'tools/call',
      'tools/call',
    ])
  })
})
