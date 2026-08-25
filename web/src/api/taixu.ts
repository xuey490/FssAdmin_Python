import api from '@/utils/http'
import { taixuSsePost, type TaixuSseFrame, type TaixuSseOptions } from '@/utils/taixu/taixu-sse'

export interface TaixuDocumentItem {
  id: string
  tenant_id: number
  document_name: string
  document_type: string
  document_size: number
  library_number: string
  document_summary?: string
  upload_time?: string | null
  index_status?: string
  index_progress?: number
  index_message?: string
}

export interface TaixuPageResult<T> {
  total: number
  pages?: number
  records: T[]
}

export interface TaixuModelItem {
  id: string
  model_name?: string
  display_name?: string
  model_id?: string
  base_url?: string
  api_key?: string
  type?: string
  source?: string
  create_time?: string
}

export interface TaixuModelMeta {
  types: Array<{ value: string; label: string }>
  sources: Array<{ value: string; label: string }>
}

export interface TaixuUserItem {
  id: string
  user_name: string
  phone_number?: string
  email?: string
  resume?: string
  photo?: string
  create_time?: string
}

export interface TaixuDocumentPageResult {
  total: number
  pages: number
  records: TaixuDocumentItem[]
}

export function fetchTaixuHomeWeather(cityCode: string) {
  return api.get<any>({ url: '/api/taixu/home/current_weather', params: { cityCode } })
}

export function fetchTaixuHomeStats() {
  return api.get<any>({ url: '/api/taixu/home/refresh_statistics' })
}

export function fetchTaixuModels(params?: Record<string, any>) {
  return api.get<TaixuPageResult<TaixuModelItem>>({ url: '/api/taixu/model/page', params })
}

export function fetchTaixuModelMeta() {
  return api.get<TaixuModelMeta>({ url: '/api/taixu/model/meta' })
}

export function fetchTaixuModelList(params?: Record<string, any>) {
  return api.get<any>({ url: '/api/taixu/model/list', params })
}

export function createTaixuModel(data: Record<string, any>) {
  return api.post<any>({ url: '/api/taixu/model/add', data })
}

export function updateTaixuModel(data: Record<string, any>) {
  return api.post<any>({ url: '/api/taixu/model/update', data })
}

export function deleteTaixuModel(data: Record<string, any>) {
  return api.post<any>({ url: '/api/taixu/model/delete', data })
}

export function fetchTaixuSettings(params?: Record<string, any>) {
  return api.get<any>({ url: '/api/taixu/setting/list', params })
}

export function fetchTaixuSettingDetail(source: string) {
  return api.get<any>({ url: '/api/taixu/setting/detail', params: { source } })
}

export function saveTaixuSettings(data: Record<string, any>) {
  return api.post<any>({ url: '/api/taixu/setting/save', data })
}

export function fetchTaixuUsers(params?: Record<string, any>) {
  return api.get<TaixuPageResult<TaixuUserItem>>({ url: '/api/taixu/user/page', params })
}

export function createTaixuUser(data: Record<string, any>) {
  return api.post<any>({ url: '/api/taixu/user/add', data })
}

export function updateTaixuUser(data: Record<string, any>) {
  return api.post<any>({ url: '/api/taixu/user/update', data })
}

export function deleteTaixuUser(data: Record<string, any>) {
  return api.post<any>({ url: '/api/taixu/user/delete', data })
}

export function fetchTaixuDocuments(params: { current_page?: number; page_size?: number; document_name?: string } = {}) {
  return api.get<TaixuDocumentPageResult>({ url: '/api/taixu/document/list', params })
}

export function deleteTaixuDocuments(data: { ids: string; current_page?: number; page_size?: number }) {
  return api.post<TaixuDocumentPageResult>({ url: '/api/taixu/document/delete', data })
}

export function uploadTaixuDocument(file: File) {
  const form = new FormData()
  form.append('file', file)
  return api.post<any>({
    url: '/api/taixu/document/upload',
    data: form,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function uploadTaixuWebsite(website: string) {
  return api.post<any>({ url: '/api/taixu/document/website', data: { website } })
}

export function previewTaixuDocument(params: { documentName: string; documentType: string }) {
  return api.get<string>({ url: '/api/taixu/document/preview', params })
}

export function downloadTaixuDocument(data: { documentName: string }) {
  return api.post<Blob>({ url: '/api/taixu/document/download', data, responseType: 'blob' })
}

export function fetchTaixuDocumentIndexStatus(ids: string[]) {
  if (!ids.length) return Promise.resolve([])
  return api.get<any>({ url: '/api/taixu/document/index-status', params: { ids: ids.join(',') } })
}

export function reindexTaixuDocuments(data: { ids: string }) {
  return api.post<{ queued: number; ids: string[] }>({ url: '/api/taixu/document/reindex', data })
}

export interface TaixuDocumentQueueStatus {
  paused: boolean
  has_login: boolean
  running: boolean
  queue_length?: number
  enqueued_count?: number
}

export function fetchTaixuDocumentQueueStatus() {
  return api.get<TaixuDocumentQueueStatus>({ url: '/api/taixu/document/queue/status' })
}

export function pauseTaixuDocumentQueue() {
  return api.post<TaixuDocumentQueueStatus>({ url: '/api/taixu/document/queue/pause', data: {} })
}

export function resumeTaixuDocumentQueue() {
  return api.post<TaixuDocumentQueueStatus>({ url: '/api/taixu/document/queue/resume', data: {} })
}

export interface TaixuDocumentQueueHealth {
  worker_connected: boolean
  worker_status: string
  last_consumed_at?: number | null
  last_error_at?: number | null
  last_error_message?: string | null
}

export function fetchTaixuDocumentQueueHealth() {
  return api.get<TaixuDocumentQueueHealth>({ url: '/api/taixu/document/queue/health' })
}

export interface TaixuHistoryPageResult {
  total: number
  pages: number
  records: Array<{
    id: string
    name: string
    source: string
    pattern: string
    library?: string
    create_time: string
    chat_model_id?: string
  }>
}

export function fetchTaixuHistoryRecords(
  params: { source?: string; pattern?: string; library?: string; name?: string; current_page?: number; page_size?: number } = {}
) {
  return api.get<TaixuHistoryPageResult | any[]>({ url: '/api/taixu/history/records', params })
}

export function fetchTaixuMemoryDetails(params: { source_id: string }) {
  return api.get<any>({ url: '/api/taixu/memory/details', params })
}

export function deleteTaixuHistory(data: { ids: string }) {
  return api.post<any>({ url: '/api/taixu/history/delete', data })
}

export function updateTaixuHistory(data: { id: string; name: string }) {
  return api.post<any>({ url: '/api/taixu/history/update', data })
}

export function updateTaixuHistoryModels(data: { id: string; chat_model_id?: string }) {
  return api.post<any>({ url: '/api/taixu/history/update-models', data })
}

export function downloadTaixuMemory(data: { source_id: string }) {
  return api.post<Blob>({ url: '/api/taixu/memory/download', data, responseType: 'blob' })
}

export function taixuRetrievalRag(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/retrieval/rag', body, onFrame, options)
}

export function taixuRetrievalAdvance(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/retrieval/advance', body, onFrame, options)
}

export function taixuSpecialRag(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/special/rag', body, onFrame, options)
}

export function taixuProgramRetrieve(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/program/retrieve', body, onFrame, options)
}

export function taixuArxivRetrieve(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/arxiv/retrieve', body, onFrame, options)
}

export function taixuAgentInvoke(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/agent/invoke', body, onFrame, options)
}

export function taixuAgenticInvoke(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/agentic/invoke', body, onFrame, options)
}

export function taixuSearchInvoke(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/search/invoke', body, onFrame, options)
}

export function taixuTopicInvoke(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/topic/invoke', body, onFrame, options)
}

export function taixuTravelInvoke(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/travel/invoke', body, onFrame, options)
}

export function taixuLlmChat(body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: TaixuSseOptions) {
  return taixuSsePost('/api/taixu/llm/chat', body, onFrame, options)
}

export function taixuGenerateImage(params: { query: string; size?: string; format?: string }) {
  return api.get<string>({ url: '/api/taixu/image/generate', params })
}

export type { TaixuSseFrame, TaixuSseOptions }
