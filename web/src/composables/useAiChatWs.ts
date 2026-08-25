import { ref, shallowRef } from 'vue'
import type { AiWsEnvelope, AiWsServerEvent, AiWsClientEvent } from './ai-ws.types'

export type { AiWsEnvelope, AiWsServerEvent }

function wsBaseUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  // 与 HTTP 共用 VITE_API_URL 前缀，生产环境走同一反向代理（/nest-api → 8181）
  const apiPrefix = String(import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
  return `${proto}//${location.host}${apiPrefix}/ws/ai`
}

export function useAiChatWs() {
  const connected = ref(false)
  const authed = ref(false)
  const connecting = ref(false)
  const lastError = ref('')
  const wsRef = shallowRef<WebSocket | null>(null)
  const handlers = new Map<AiWsServerEvent, Set<(data: any) => void>>()

  const on = (event: AiWsServerEvent, fn: (data: any) => void) => {
    if (!handlers.has(event)) handlers.set(event, new Set())
    handlers.get(event)!.add(fn)
    return () => handlers.get(event)?.delete(fn)
  }

  const emitLocal = (event: AiWsServerEvent, data: unknown) => {
    handlers.get(event)?.forEach((fn) => fn(data))
  }

  const send = (event: AiWsClientEvent, data: unknown) => {
    const ws = wsRef.value
    if (!ws || ws.readyState !== WebSocket.OPEN) return false
    ws.send(JSON.stringify({ event, data } satisfies AiWsEnvelope))
    return true
  }

  const connect = (token: string) =>
    new Promise<void>((resolve, reject) => {
      if (wsRef.value?.readyState === WebSocket.OPEN && authed.value) {
        resolve()
        return
      }

      connecting.value = true
      lastError.value = ''

      if (wsRef.value) {
        wsRef.value.close()
        wsRef.value = null
      }

      const url = wsBaseUrl()
      const ws = new WebSocket(url)
      wsRef.value = ws

      const timeout = window.setTimeout(() => {
        if (!authed.value) {
          finish(new Error(`WebSocket 连接超时（${url}），请确认后端已启动且反向代理已转发该路径`))
        }
      }, 15000)

      let settled = false
      const finish = (err?: Error) => {
        if (settled) return
        settled = true
        window.clearTimeout(timeout)
        connecting.value = false
        if (err) {
          lastError.value = err.message
          reject(err)
        } else {
          lastError.value = ''
          resolve()
        }
      }

      ws.onopen = () => {
        connected.value = true
        send('auth', { token })
      }

      ws.onmessage = (ev) => {
        let msg: AiWsEnvelope
        try {
          msg = JSON.parse(String(ev.data))
        } catch {
          return
        }

        const event = msg.event as AiWsServerEvent
        if (event === 'auth.ok') {
          authed.value = true
          finish()
        }
        if (event === 'auth.error') {
          authed.value = false
          finish(new Error((msg.data as any)?.message || 'WebSocket 鉴权失败'))
        }
        emitLocal(event, msg.data)
      }

      ws.onerror = () => {
        connected.value = false
        finish(new Error(`WebSocket 连接失败（${url}），请检查反向代理是否支持 WebSocket 升级`))
      }

      ws.onclose = () => {
        connected.value = false
        authed.value = false
        wsRef.value = null
        connecting.value = false
      }
    })

  const chatSend = (payload: {
    session_uuid: string
    content: string
    model_id?: string
  }) => send('chat.send', payload)

  const chatStop = (payload: { session_uuid: string; message_uuid?: string }) =>
    send('chat.stop', payload)

  const disconnect = () => {
    wsRef.value?.close()
    wsRef.value = null
    connected.value = false
    authed.value = false
  }

  return {
    connected,
    authed,
    connecting,
    lastError,
    connect,
    disconnect,
    on,
    chatSend,
    chatStop
  }
}
