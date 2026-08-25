import { ref, reactive, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchTaixuModelList, fetchTaixuSettingDetail, saveTaixuSettings } from '@/api/taixu'
import type { TaixuModelItem } from '@/api/taixu'

export function formatModelOptionLabel(model: TaixuModelItem) {
  const name = model.model_name || model.model_id || model.display_name || model.id
  const source = model.source || ''
  return `${name} (${source})`
}

function normalizeContent(raw: unknown): Record<string, any> {
  if (!raw) return {}
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw)
    } catch {
      return {}
    }
  }
  if (typeof raw === 'object' && raw !== null && 'content' in (raw as Record<string, any>)) {
    return normalizeContent((raw as Record<string, any>).content)
  }
  return raw as Record<string, any>
}

export function useSettingPanel(
  source: string,
  modelType: 'llm' | 'embedding',
  defaults: Record<string, string>,
  active: Ref<boolean>
) {
  const loading = ref(false)
  const saving = ref(false)
  const models = ref<TaixuModelItem[]>([])
  const form = reactive({ ...defaults })

  const loadModels = async () => {
    models.value = await fetchTaixuModelList({ type: modelType })
  }

  const applyContent = (raw: unknown = {}) => {
    Object.assign(form, defaults)
    const content = normalizeContent(raw)
    Object.keys(defaults).forEach((key) => {
      if (content[key] != null && content[key] !== '') {
        ;(form as Record<string, string>)[key] = String(content[key])
      }
    })
  }

  const load = async () => {
    loading.value = true
    try {
      await loadModels()
      const row = await fetchTaixuSettingDetail(source)
      applyContent(row?.content ?? row)
    } catch (e: any) {
      ElMessage.error(e?.message || '加载失败')
    } finally {
      loading.value = false
    }
  }

  watch(
    active,
    (val) => {
      if (val) void load()
    },
    { immediate: true }
  )

  const onModelChange = (sourceId: string) => {
    const model = models.value.find((item) => item.id === sourceId)
    if (!model) return
    form.sourceId = model.id
    form.model = model.model_name || model.model_id || model.display_name || ''
    form.type = model.source || ''
    form.baseUrl = model.base_url || ''
    form.apiKey = model.api_key || ''
  }

  const reset = () => {
    Object.assign(form, defaults)
  }

  const save = async () => {
    saving.value = true
    try {
      const selected = models.value.find((item) => item.id === form.sourceId)
      const payload = {
        source,
        ...form,
        model: selected?.model_name || form.model
      }
      const saved = await saveTaixuSettings(payload)
      applyContent(saved?.content ?? saved ?? payload)
      ElMessage.success('保存成功')
    } catch (e: any) {
      ElMessage.error(e?.message || '保存失败')
    } finally {
      saving.value = false
    }
  }

  return {
    loading,
    saving,
    models,
    form,
    load,
    onModelChange,
    reset,
    save,
    formatModelOptionLabel
  }
}
