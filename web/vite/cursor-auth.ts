import os from 'node:os'
import path from 'node:path'
import Database from 'better-sqlite3'

const CURSOR_DB_PATH = path.join(
  os.homedir(),
  'Library',
  'Application Support',
  'Cursor',
  'User',
  'globalStorage',
  'state.vscdb'
)

const CACHE_TTL_MS = 5 * 60 * 1000

let cachedCookie: string | null = null
let cachedAt = 0
let loggedOnce = false

function readAccessToken(): string | null {
  try {
    const db = new Database(CURSOR_DB_PATH, { readonly: true, fileMustExist: true })
    try {
      const row = db
        .prepare("SELECT value FROM ItemTable WHERE key = 'cursorAuth/accessToken'")
        .get() as { value?: string } | undefined
      return row?.value ?? null
    } finally {
      db.close()
    }
  } catch (err) {
    console.warn('[cursor-proxy] could not build cookie:', (err as Error).message)
    return null
  }
}

function decodeJwtSub(jwt: string): string | null {
  try {
    const parts = jwt.split('.')
    if (parts.length < 2) return null
    const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'))
    if (typeof payload.sub !== 'string') return null
    return payload.sub
  } catch (err) {
    console.warn('[cursor-proxy] could not build cookie:', (err as Error).message)
    return null
  }
}

function buildCookieHeader(): string | null {
  const token = readAccessToken()
  if (!token) {
    console.warn('[cursor-proxy] could not build cookie: no access token found in state.vscdb')
    return null
  }

  const sub = decodeJwtSub(token)
  if (!sub) {
    console.warn('[cursor-proxy] could not build cookie: could not decode JWT sub')
    return null
  }

  const userId = sub.startsWith('auth0|') ? sub.slice('auth0|'.length) : sub
  const cookieValue = `${userId}::${token}`
  const encoded = encodeURIComponent(cookieValue)

  if (!loggedOnce) {
    console.log('[cursor-proxy] cookie built for user:', userId)
    loggedOnce = true
  }

  return `WorkosCursorSessionToken=${encoded}`
}

export function getCursorCookie(): string | null {
  const now = Date.now()
  if (cachedCookie && now - cachedAt < CACHE_TTL_MS) {
    return cachedCookie
  }
  const cookie = buildCookieHeader()
  cachedCookie = cookie
  cachedAt = now
  return cookie
}
