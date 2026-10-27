const MCP_ENDPOINT = import.meta.env.PROD ? '/mcp' : '/proxy/mcp'
const PROTOCOL_VERSION = '2025-06-18'

type JsonRpcError = {
  code: number
  message: string
  data?: unknown
}

type JsonRpcResponse = {
  jsonrpc: '2.0'
  id?: number
  result?: unknown
  error?: JsonRpcError
}

type ToolCallResult = {
  structuredContent?: unknown
  content?: Array<{ type?: string; text?: string }>
  isError?: boolean
}

export class McpError extends Error {
  constructor(
    message: string,
    readonly code?: number,
    readonly data?: unknown,
    readonly status?: number,
  ) {
    super(message)
    this.name = 'McpError'
  }
}

let nextRequestId = 1
let sessionId: string | undefined
let initialization: Promise<void> | undefined

function parseSseEvent(event: string): JsonRpcResponse | undefined {
  const data = event
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
  return data ? (JSON.parse(data) as JsonRpcResponse) : undefined
}

async function parseSse(response: Response): Promise<JsonRpcResponse> {
  if (!response.body) throw new McpError('MCP SSE response had no body')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffered = ''

  while (true) {
    const { done, value } = await reader.read()
    buffered += decoder.decode(value, { stream: !done })

    let boundary = buffered.match(/\r?\n\r?\n/)
    while (boundary?.index !== undefined) {
      const event = buffered.slice(0, boundary.index)
      buffered = buffered.slice(boundary.index + boundary[0].length)
      const message = parseSseEvent(event)
      if (message) {
        // Streamable HTTP returns one final JSON-RPC response for this request.
        // Stop reading once that complete event arrives instead of waiting for
        // a server-managed SSE stream to close.
        await reader.cancel()
        return message
      }
      boundary = buffered.match(/\r?\n\r?\n/)
    }

    if (done) {
      const message = parseSseEvent(buffered)
      if (message) return message
      break
    }
  }
  throw new McpError('MCP SSE response did not contain a data event')
}

async function parseResponse(response: Response): Promise<JsonRpcResponse | undefined> {
  if (!response.ok) {
    const detail = await response.text()
    throw new McpError(
      `MCP HTTP ${response.status}${detail ? `: ${detail}` : ''}`,
      undefined,
      undefined,
      response.status,
    )
  }

  const returnedSession = response.headers.get('Mcp-Session-Id')
  if (returnedSession) sessionId = returnedSession

  if (response.status === 202 || response.status === 204) return undefined

  if (response.headers.get('Content-Type')?.includes('text/event-stream')) {
    return parseSse(response)
  }

  const body = await response.text()
  return body ? (JSON.parse(body) as JsonRpcResponse) : undefined
}

async function send(
  payload: Record<string, unknown>,
  includeSession = true,
): Promise<JsonRpcResponse | undefined> {
  const headers = new Headers({
    Accept: 'application/json, text/event-stream',
    'Content-Type': 'application/json',
  })
  if (includeSession && sessionId) headers.set('Mcp-Session-Id', sessionId)

  const response = await fetch(MCP_ENDPOINT, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })
  const message = await parseResponse(response)
  if (message?.error) {
    throw new McpError(message.error.message, message.error.code, message.error.data)
  }
  return message
}

async function initialize(): Promise<void> {
  const id = nextRequestId++
  await send(
    {
      jsonrpc: '2.0',
      id,
      method: 'initialize',
      params: {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: {},
        clientInfo: { name: 'sb-web', version: '0.1.0' },
      },
    },
    false,
  )

  await send({
    jsonrpc: '2.0',
    method: 'notifications/initialized',
  })
}

function resetSession(): void {
  sessionId = undefined
  initialization = undefined
}

function ensureInitialized(): Promise<void> {
  if (!initialization) {
    const attempt = initialize()
    initialization = attempt
    void attempt.catch(() => {
      if (initialization === attempt) resetSession()
    })
  }
  return initialization
}

function extractToolResult<T>(result: ToolCallResult): T {
  const errorText = result.content?.find((item) => item.type === 'text')?.text
  if (result.isError) throw new McpError(errorText || 'MCP tool call failed')

  if (result.structuredContent !== undefined) {
    const structured = result.structuredContent
    if (
      structured !== null &&
      typeof structured === 'object' &&
      Object.prototype.hasOwnProperty.call(structured, 'result')
    ) {
      return (structured as { result: T }).result
    }
    return structured as T
  }

  if (errorText !== undefined) {
    try {
      const parsed = JSON.parse(errorText) as T | { result: T }
      if (
        parsed !== null &&
        typeof parsed === 'object' &&
        Object.prototype.hasOwnProperty.call(parsed, 'result')
      ) {
        return (parsed as { result: T }).result
      }
      return parsed as T
    } catch (error) {
      if (error instanceof SyntaxError) throw new McpError('MCP tool returned non-JSON text')
      throw error
    }
  }

  throw new McpError('MCP tool returned no structured or JSON content')
}

export async function callTool<T>(
  name: string,
  args: Record<string, unknown> = {},
): Promise<T> {
  await ensureInitialized()

  const id = nextRequestId++
  let response: JsonRpcResponse | undefined
  try {
    response = await send({
      jsonrpc: '2.0',
      id,
      method: 'tools/call',
      params: { name, arguments: args },
    })
  } catch (error) {
    if (error instanceof McpError && error.status === 404 && sessionId) resetSession()
    throw error
  }
  if (!response || response.result === undefined) {
    throw new McpError(`MCP tool ${name} returned no result`)
  }
  return extractToolResult<T>(response.result as ToolCallResult)
}
