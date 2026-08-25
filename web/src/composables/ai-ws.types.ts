export type AiWsClientEvent = 'auth' | 'chat.send' | 'chat.stop' | 'ping'

export type AiWsServerEvent =
  | 'auth.ok'
  | 'auth.error'
  | 'pong'
  | 'chat.user_message'
  | 'chat.message_start'
  | 'chat.token'
  | 'chat.message_done'
  | 'chat.error'

export interface AiWsEnvelope<T = unknown> {
  event: AiWsClientEvent | AiWsServerEvent
  request_id?: string
  data: T
}
