export const TAIXU_MODEL_TYPE_OPTIONS = [
  { value: 'llm', label: 'LLM' },
  { value: 'embedding', label: 'Embedding' },
  { value: 'medical', label: 'Medical' },
  { value: 'vision', label: 'Vision' }
] as const

export const TAIXU_MODEL_SOURCE_OPTIONS = [
  { value: 'ollama', label: 'Ollama' },
  { value: 'modelscope', label: 'ModelScope' },
  { value: 'cloud', label: 'Cloud' },
  { value: 'gitee', label: 'Gitee' }
] as const

export type TaixuModelTypeValue = (typeof TAIXU_MODEL_TYPE_OPTIONS)[number]['value']
export type TaixuModelSourceValue = (typeof TAIXU_MODEL_SOURCE_OPTIONS)[number]['value']

export function getTaixuModelTypeLabel(value?: string) {
  return TAIXU_MODEL_TYPE_OPTIONS.find((item) => item.value === value)?.label || value || '-'
}

export function getTaixuModelSourceLabel(value?: string) {
  return TAIXU_MODEL_SOURCE_OPTIONS.find((item) => item.value === value)?.label || value || '-'
}
