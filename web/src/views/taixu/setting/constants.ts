export const SETTING_TABS = [
  { key: 'llm', label: 'LLM设置', icon: 'ri:cpu-line' },
  { key: 'rag', label: 'RAG设置', icon: 'ri:git-merge-line' },
  { key: 'agent', label: 'Agent设置', icon: 'ri:robot-2-line' },
  { key: 'memory', label: 'Memory设置', icon: 'ri:database-2-line' },
 // { key: 'profile', label: '个人中心', icon: 'ri:shield-user-line', placeholder: true },
 // { key: 'style', label: '样式设置', icon: 'ri:palette-line', placeholder: true }
] as const

export type SettingTabKey = (typeof SETTING_TABS)[number]['key']

export const LLM_DEFAULTS = {
  sourceId: '',
  model: '',
  type: '',
  baseUrl: '',
  apiKey: '',
  temperature: '0.3'
}

export const RAG_DEFAULTS = {
  sourceId: '',
  model: '',
  type: '',
  baseUrl: '',
  apiKey: '',
  dimensions: '1024',
  topK: '3',
  chunkSize: '768',
  chunkOverlap: '50',
  distance: 'COSINE',
  hybrid: 'close',
  combine: 'rrf',
  graph: 'close',
  method: 'community'
}

export const AGENT_DEFAULTS = {
  sourceId: '',
  model: '',
  type: '',
  baseUrl: '',
  apiKey: '',
  temperature: '0.3',
  maxIterations: '10'
}

export const MEMORY_DEFAULTS = {
  sourceId: '',
  model: '',
  type: '',
  baseUrl: '',
  apiKey: '',
  topK: '5',
  windowSize: '10'
}
