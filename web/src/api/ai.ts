import api from '@/utils/http'

export interface AiModelOption {
  id: string
  model_code: string
  name: string
  provider_id: string
  provider_name: string
  is_default: boolean
  default_temperature: number
}

export interface AiSessionItem {
  session_uuid: string
  title: string
  default_model_id: string | null
  message_count: number
  last_message_at: string | null
  create_time: string
}

export interface AiMessageItem {
  message_uuid: string
  role: 'user' | 'assistant'
  content: string
  status: string
  model_id: string | null
  model_name: string | null
  provider_name: string | null
  create_time: string
}

export interface AiSessionStats {
  total_tokens: number
  rounds: number
  context_window: number
  compact_threshold: number
  /** 本次请求 */
  turn_tokens?: number
  turn_prompt_tokens?: number
  cache_hit_rate?: number | null
  context_ratio?: number
}

export function fetchAiModelOptions() {
  return api.get<{ list: AiModelOption[] }>({ url: '/api/ai/models/options' })
}

export function fetchAiSessions(params?: { page?: number; limit?: number }) {
  return api.get<{ list: AiSessionItem[]; total: number }>({ url: '/api/ai/sessions', params })
}

export function fetchCreateAiSession(body?: { model_id?: string; agent_id?: string; title?: string }) {
  return api.post<{
    session_uuid: string
    title: string
    default_model_id: string
  }>({ url: '/api/ai/sessions', data: body })
}

export function fetchAiMessages(sessionUuid: string) {
  return api.get<{ session_uuid: string; default_model_id: string; stats: AiSessionStats; list: AiMessageItem[] }>({
    url: `/api/ai/sessions/${sessionUuid}/messages`
  })
}

export function fetchUpdateSessionModel(sessionUuid: string, modelId: string) {
  return api.request({ url: `/api/ai/sessions/${sessionUuid}/model`, method: 'PATCH', data: { model_id: modelId } })
}

export function fetchUpdateSessionTitle(sessionUuid: string, title: string) {
  return api.request({ url: `/api/ai/sessions/${sessionUuid}/title`, method: 'PATCH', data: { title } })
}

export function fetchDeleteAiSession(sessionUuid: string) {
  return api.del({ url: `/api/ai/sessions/${sessionUuid}` })
}
