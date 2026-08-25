import { useUserStore } from '@/store/modules/user'

export type TaixuSseFrameType = 'event' | 'think' | 'data'

export interface TaixuSseFrame {
  type: TaixuSseFrameType
  payload: string
}

export interface TaixuSseOptions {
  signal?: AbortSignal
  headers?: Record<string, string>
}

function parseFrame(text: string): TaixuSseFrame | null {
  const lines = text.split('\n')
  const payloadMap: Record<TaixuSseFrameType, string[]> = { event: [], think: [], data: [] }
  const fallback: string[] = []
  let firstType: TaixuSseFrameType | null = null

  for (const line of lines) {
    if (!line || line.startsWith(':')) continue
    const idx = line.indexOf(':')
    if (idx <= 0) {
      if (firstType) {
        // ponytail: tolerate malformed SSE continuation lines from legacy server writes
        payloadMap[firstType].push(line)
        continue
      }
      fallback.push(line)
      continue
    }

    const rawType = line.slice(0, idx).trim()
    let payload = line.slice(idx + 1)
    if (payload.startsWith(' ')) payload = payload.slice(1)

    if (rawType === 'event' || rawType === 'think' || rawType === 'data') {
      payloadMap[rawType].push(payload)
      if (!firstType) firstType = rawType
      continue
    }
    fallback.push(line)
  }

  if (firstType) {
    return { type: firstType, payload: payloadMap[firstType].join('\n') }
  }
  if (fallback.length) {
    return { type: 'data', payload: fallback.join('\n') }
  }
  return null
}

export async function taixuSsePost(
  url: string,
  body: unknown,
  onFrame: (frame: TaixuSseFrame) => void,
  options: TaixuSseOptions = {}
) {
  const userStore = useUserStore()
  const token = (userStore as any).accessToken || ''
  const apiBase = (import.meta as any).env?.VITE_API_URL || ''
  const fullUrl = (() => {
    const u = url.startsWith('/') ? url : `/${url}`
    if (!apiBase) return u
    const base = String(apiBase).replace(/\/+$/, '')
    return `${base}${u}`
  })()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(fullUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify(body ?? {}),
    signal: options.signal
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('text/event-stream')) {
    const text = await res.text().catch(() => '')
    throw new Error(text || 'Non-SSE response')
  }
  if (!res.body) return

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n')

    let idx = buffer.indexOf('\n\n')
    while (idx !== -1) {
      const block = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const frame = parseFrame(block)
      if (frame) onFrame(frame)
      idx = buffer.indexOf('\n\n')
    }
  }

  const tail = buffer.trim()
  if (tail) {
    const frame = parseFrame(tail)
    if (frame) onFrame(frame)
  }
}
