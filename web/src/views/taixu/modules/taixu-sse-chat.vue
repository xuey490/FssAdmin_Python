<template>
  <div class="taixu-sse-chat art-full-height">
    <ElCard shadow="never" class="chat-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <ElTag type="info">{{ title }}</ElTag>
          <ElButton :disabled="streaming" @click="handleNewSession">新会话</ElButton>
          <ElTag v-if="streaming" type="warning">生成中...</ElTag>
          <ElTag v-else type="success">就绪</ElTag>
        </div>
        <div v-if="streaming" class="stream-progress">
          <ElProgress :percentage="streamProgress" :stroke-width="8" />
          <span class="stream-stage">{{ streamStage || '检索分析中…' }}</span>
        </div>
        <div class="toolbar-right">
          <ElButton v-if="streaming" type="warning" @click="handleStop">停止</ElButton>
        </div>
      </div>

      <div class="content">
        <div class="chat-panel">
          <div ref="messageListRef" class="message-list">
            <div v-for="msg in messages" :key="msg.id" class="message-row" :class="msg.role">
              <div class="message-inner">
                <div class="message-meta">
                  <span class="role-label">{{ msg.role === 'user' ? '我' : 'AI' }}</span>
                </div>
                <div v-if="msg.role === 'user'" class="user-bubble">{{ msg.content }}</div>
                <div v-else class="assistant-bubble">
                  <ElCollapse v-if="msg.thinks.length" class="think-collapse">
                    <ElCollapseItem title="思考过程" name="think">
                      <div class="think-content">
                        <div v-for="(t, idx) in msg.thinks" :key="idx" class="think-line">{{ t }}</div>
                      </div>
                    </ElCollapseItem>
                  </ElCollapse>
                  <MdPreview
                    :key="streamingMsgId === msg.id ? `body-${msg.id}-${streamPreviewTick}` : `body-${msg.id}`"
                    :model-value="msg.content || (streaming && msg.id === streamingMsgId ? '...' : '')"
                    preview-theme="github"
                    :theme="previewTheme"
                    :code-theme="codeTheme"
                  />
                </div>
              </div>
            </div>
          </div>

          <div class="composer">
            <ElInput
              v-model="inputText"
              type="textarea"
              :rows="3"
              placeholder="输入问题，Enter 发送（Shift+Enter 换行）"
              :disabled="streaming"
              @keydown.enter.exact.prevent="handleSend"
            />
            <div class="composer-actions">
              <ElButton
                type="primary"
                :loading="streaming"
                :disabled="!canSend"
                @click="handleSend"
              >
                智能答疑
              </ElButton>
            </div>
          </div>
        </div>

        <div class="side-panel">
          <ElTabs v-model="activeTab">
            <ElTabPane label="检索信息" name="settings">
              <div class="settings-readout">
                <div class="settings-row">
                  <span class="settings-label">文本模型：</span>
                  <span class="settings-value" :title="llmDisplay">{{ llmDisplay }}</span>
                </div>
                <div class="settings-row">
                  <span class="settings-label">检索模型：</span>
                  <span class="settings-value" :title="ragDisplay">{{ ragDisplay }}</span>
                </div>
                <div class="settings-note">注：配置详情见【设置管理】</div>
              </div>
              <ElForm label-width="72px" label-align="left">
                <ElFormItem v-if="patternVisible" label="模式">
                  <ElSelect
                    v-model="selectedPattern"
                    style="width: 100%"
                    placeholder="选择模式"
                    :disabled="streaming"
                  >
                    <ElOption
                      v-for="p in patternOptions"
                      :key="p.value"
                      :label="p.label"
                      :value="p.value"
                    />
                  </ElSelect>
                </ElFormItem>
                <ElFormItem v-if="showLibrary" label="知识库">
                  <ElSelect
                    v-model="selectedLibrary"
                    style="width: 100%"
                    placeholder="选择私有知识库"
                    :disabled="streaming"
                    filterable
                    clearable
                    @change="handleLibraryChange"
                    @clear="handleLibraryChange"
                  >
                    <ElOption
                      v-for="d in libraryOptions"
                      :key="d.value"
                      :label="d.label"
                      :value="d.value"
                    />
                  </ElSelect>
                </ElFormItem>
              </ElForm>
            </ElTabPane>
            <ElTabPane label="历史对话" name="history">
              <div class="history-toolbar">
                <ElInput
                  v-model="historyKeyword"
                  placeholder="搜索会话"
                  clearable
                  @keyup.enter="searchHistory"
                  @clear="searchHistory"
                />
                <ElButton :loading="loadingHistory" @click="searchHistory">搜索</ElButton>
              </div>
              <ElTable
                height="420"
                border
                :data="historyList"
                highlight-current-row
                @current-change="handleSelectHistory"
              >
                <ElTableColumn label="标题" min-width="140" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span :title="row.name">{{ truncateHistoryTitle(row.name) }}</span>
                  </template>
                </ElTableColumn>
                <ElTableColumn label="操作" width="80" align="center">
                  <template #default="{ row }">
                    <ElButton link type="primary" :icon="EditPen" title="重命名" @click.stop="renameDialog(row)" />
                    <ElButton link type="danger" :icon="Delete" title="删除" @click.stop="deleteDialog(row)" />
                  </template>
                </ElTableColumn>
              </ElTable>
              <div class="history-pagination">
                <ElPagination
                  v-model:current-page="historyPage"
                  v-model:page-size="historyPageSize"
                  :total="historyTotal"
                  :page-sizes="[10, 20, 50]"
                  layout="total, sizes, prev, pager, next"
                  background
                  small
                  @current-change="loadHistory"
                  @size-change="onHistoryPageSizeChange"
                />
              </div>
            </ElTabPane>
          </ElTabs>
        </div>
      </div>
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { Delete, EditPen } from '@element-plus/icons-vue'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { MdPreview } from 'md-editor-v3'
  import 'md-editor-v3/lib/style.css'
  import { useSettingStore } from '@/store/modules/setting'
  import {
    deleteTaixuHistory,
    fetchTaixuDocuments,
    fetchTaixuHistoryRecords,
    fetchTaixuMemoryDetails,
    fetchTaixuSettingDetail,
    updateTaixuHistory,
    type TaixuDocumentItem,
    type TaixuHistoryPageResult,
    type TaixuSseFrame
  } from '@/api/taixu'

  export interface PatternOption {
    label: string
    value: string
  }

  export interface EndpointFn {
    (
      body: Record<string, any>,
      onFrame: (frame: TaixuSseFrame) => void,
      options?: { signal?: AbortSignal }
    ): Promise<void>
  }

  interface ChatMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    thinks: string[]
  }

  interface HistoryRow {
    id: string
    name: string
    source: string
    pattern: string
    library?: string
    create_time: string
  }

  interface LlmConnectConfig {
    sourceId: string
    model: string
    type: string
    baseUrl: string
    apiKey: string
    temperature: string
  }

  const props = withDefaults(
    defineProps<{
      title: string
      source: string
      endpoint: EndpointFn
      patternOptions: PatternOption[]
      defaultPattern?: string
      patternVisible?: boolean
      showLibrary?: boolean
      welcomeMessage?: string
    }>(),
    {
      defaultPattern: '',
      patternVisible: true,
      showLibrary: false,
      welcomeMessage: '你好！！我是 TaiXu 智能助手，有什么可以帮您？'
    }
  )

  const settingStore = useSettingStore()
  const previewTheme = computed(() => (settingStore.isDark ? 'dark' : 'light'))
  const codeTheme = computed(() => (settingStore.isDark ? 'github-dark' : 'github'))

  const activeTab = ref('settings')
  const inputText = ref('')
  const messages = ref<ChatMessage[]>([])
  const streaming = ref(false)
  const streamingMsgId = ref('')
  const streamPreviewTick = ref(0)
  const streamProgress = ref(0)
  const streamStage = ref('')
  const selectedPattern = ref(props.defaultPattern || props.patternOptions[0]?.value || '')
  const selectedLibrary = ref('')
  const libraryOptions = ref<Array<{ label: string; value: string }>>([])
  const messageListRef = ref<HTMLElement>()
  const sourceId = ref('')

  const historyKeyword = ref('')
  const loadingHistory = ref(false)
  const historyList = ref<HistoryRow[]>([])
  const historyPage = ref(1)
  const historyPageSize = ref(10)
  const historyTotal = ref(0)

  const llmConfig = reactive<LlmConnectConfig>({
    sourceId: '',
    model: '',
    type: '',
    baseUrl: '',
    apiKey: '',
    temperature: '0.3'
  })
  const ragDisplayModel = ref('')

  const patternVisible = computed(() => Boolean(props.patternVisible))
  const showLibrary = computed(() => Boolean(props.showLibrary))

  const llmDisplay = computed(() => llmConfig.model || '未配置')
  const ragDisplay = computed(() => ragDisplayModel.value || '未配置')
  const canSend = computed(() => {
    if (!inputText.value.trim() || streaming.value) return false
    if (patternVisible.value && !selectedPattern.value) return false
    if (showLibrary.value && !selectedLibrary.value) return false
    return true
  })

  let abortController: AbortController | null = null
  let streamPreviewRaf = 0

  const bumpStreamPreview = () => {
    if (streamPreviewRaf) return
    streamPreviewRaf = requestAnimationFrame(() => {
      streamPreviewTick.value++
      streamPreviewRaf = 0
    })
  }

  const newId = () => {
    try {
      return crypto.randomUUID()
    } catch {
      return `${Date.now()}_${Math.random().toString(16).slice(2)}`
    }
  }

  const truncateHistoryTitle = (name?: string, max = 40) => {
    const text = String(name || '')
    return text.length > max ? `${text.slice(0, max)}...` : text
  }

  const scrollToBottom = async () => {
    await nextTick()
    const el = messageListRef.value
    if (el) el.scrollTop = el.scrollHeight
  }

  const normalizeSettingModel = (model: string, type: string) => {
    const suffix = type ? ` (${type})` : ''
    if (suffix && model.endsWith(suffix)) return model.slice(0, -suffix.length).trim()
    return model
  }

  const applyLlmSettingContent = (raw: Record<string, any> = {}) => {
    if (raw.sourceId) llmConfig.sourceId = String(raw.sourceId)
    if (raw.type) llmConfig.type = String(raw.type)
    if (raw.baseUrl) llmConfig.baseUrl = String(raw.baseUrl)
    if (raw.apiKey) llmConfig.apiKey = String(raw.apiKey)
    if (raw.temperature != null && raw.temperature !== '') llmConfig.temperature = String(raw.temperature)
    if (raw.model) llmConfig.model = normalizeSettingModel(String(raw.model), llmConfig.type)
  }

  const loadSettings = async () => {
    const [llmSetting, ragSetting] = await Promise.all([
      fetchTaixuSettingDetail('llm'),
      fetchTaixuSettingDetail('rag')
    ])
    applyLlmSettingContent((llmSetting?.content ?? llmSetting ?? {}) as Record<string, any>)
    const ragRaw = (ragSetting?.content ?? ragSetting ?? {}) as Record<string, any>
    ragDisplayModel.value = String(ragRaw.model || '')
  }

  const loadLibraries = async () => {
    if (!showLibrary.value) return
    const res = await fetchTaixuDocuments({ current_page: 1, page_size: 200 })
    const list = (res.records || []) as TaixuDocumentItem[]
    libraryOptions.value = list.map((d) => ({
      label: `${d.document_name} (${d.library_number})`,
      value: d.library_number
    }))
  }

  const normalizeHistoryResult = (res: TaixuHistoryPageResult | HistoryRow[] | null | undefined) => {
    if (Array.isArray(res)) {
      historyTotal.value = res.length
      return res as HistoryRow[]
    }
    const page = res as TaixuHistoryPageResult | undefined
    historyTotal.value = Number(page?.total ?? 0)
    return (page?.records || []) as HistoryRow[]
  }

  const currentPatternForRequest = () => selectedPattern.value || props.defaultPattern || undefined

  const currentPatternForHistory = () => (patternVisible.value ? currentPatternForRequest() : undefined)

  const currentLibraryForHistory = () => (showLibrary.value ? selectedLibrary.value || undefined : undefined)

  const loadHistory = async () => {
    loadingHistory.value = true
    try {
      const res = await fetchTaixuHistoryRecords({
        source: props.source,
        pattern: currentPatternForHistory(),
        library: currentLibraryForHistory(),
        name: historyKeyword.value.trim() || undefined,
        current_page: historyPage.value,
        page_size: historyPageSize.value
      })
      historyList.value = normalizeHistoryResult(res)
    } finally {
      loadingHistory.value = false
    }
  }

  const searchHistory = async () => {
    historyPage.value = 1
    await loadHistory()
  }

  const onHistoryPageSizeChange = async () => {
    historyPage.value = 1
    await loadHistory()
  }

  const handleLibraryChange = async () => {
    historyPage.value = 1
    await loadHistory()
  }

  const handleNewSession = () => {
    handleStop()
    sourceId.value = newId()
    messages.value = [{ id: newId(), role: 'assistant', content: props.welcomeMessage, thinks: [] }]
    inputText.value = ''
    void scrollToBottom()
  }

  const resetStreamProgress = () => {
    streamProgress.value = 0
    streamStage.value = ''
  }

  const bumpStreamProgress = (payload: string, type: TaixuSseFrame['type']) => {
    if (type === 'event') {
      if (payload === 'Connection established') {
        streamProgress.value = Math.max(streamProgress.value, 8)
        streamStage.value = '已连接'
      } else if (payload === 'History Record completed') {
        streamProgress.value = Math.max(streamProgress.value, 18)
        streamStage.value = '历史记忆已加载'
      } else if (payload === 'Streaming finished') {
        streamProgress.value = 100
        streamStage.value = '完成'
      } else if (payload.startsWith('error:')) {
        streamStage.value = payload
      } else if (payload && payload !== 'Connection established') {
        streamProgress.value = Math.min(88, streamProgress.value + 6)
        streamStage.value = payload.slice(0, 100)
      }
      return
    }
    if (type === 'think') {
      streamProgress.value = Math.min(88, streamProgress.value + 10)
      const line = payload.split('\n').find((s) => s.trim()) || payload
      streamStage.value = line.trim().slice(0, 100)
      return
    }
    if (type === 'data') {
      streamProgress.value = Math.max(streamProgress.value, 92)
      if (!streamStage.value.includes('生成')) streamStage.value = '生成回答中…'
    }
  }

  const handleStop = () => {
    abortController?.abort()
    abortController = null
    streaming.value = false
    streamingMsgId.value = ''
    resetStreamProgress()
  }

  const handleSelectHistory = async (row: HistoryRow) => {
    if (!row?.id) return
    handleStop()
    sourceId.value = row.id
    if (row.pattern) selectedPattern.value = row.pattern
    const details = await fetchTaixuMemoryDetails({ source_id: row.id })
    const list = (details || []) as Array<{ id: string; type: string; content: string }>
    const mapped: ChatMessage[] = [
      { id: newId(), role: 'assistant', content: props.welcomeMessage, thinks: [] }
    ]
    for (const item of list) {
      mapped.push({
        id: item.id || newId(),
        role: item.type === 'user' ? 'user' : 'assistant',
        content: item.content || '',
        thinks: []
      })
    }
    messages.value = mapped
    void scrollToBottom()
  }

  const renameDialog = async (row: HistoryRow) => {
    const { value } = await ElMessageBox.prompt('请输入会话标题', '重命名', {
      inputValue: row.name || '',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
    await updateTaixuHistory({ id: row.id, name: value })
    ElMessage.success('已更新')
    await loadHistory()
  }

  const deleteDialog = async (row: HistoryRow) => {
    await ElMessageBox.confirm('确定删除该会话吗？', '删除', { type: 'warning' })
    await deleteTaixuHistory({ ids: row.id })
    ElMessage.success('已删除')
    if (sourceId.value === row.id) handleNewSession()
    await loadHistory()
  }

  const handleSend = async () => {
    const q = inputText.value.trim()
    if (!q || streaming.value) return
    if (!llmConfig.model) {
      ElMessage.warning('请先在设置管理配置文本模型')
      return
    }
    if (patternVisible.value && !selectedPattern.value) {
      ElMessage.warning('请选择检索模式')
      return
    }
    if (showLibrary.value && !selectedLibrary.value) {
      ElMessage.warning('请选择知识库')
      return
    }
    if (!sourceId.value) sourceId.value = newId()

    streaming.value = true
    streamingMsgId.value = ''
    streamPreviewTick.value = 0
    resetStreamProgress()
    streamProgress.value = 3
    streamStage.value = '正在连接…'
    abortController?.abort()
    abortController = new AbortController()

    const userMsg: ChatMessage = { id: newId(), role: 'user', content: q, thinks: [] }
    const aiMsg: ChatMessage = { id: newId(), role: 'assistant', content: '', thinks: [] }
    streamingMsgId.value = aiMsg.id
    messages.value = [...messages.value, userMsg, aiMsg]
    inputText.value = ''
    await scrollToBottom()

    const getTarget = () => messages.value.find((m) => m.id === aiMsg.id)

    const onFrame = (frame: TaixuSseFrame) => {
      const target = getTarget()
      if (!target) return
      bumpStreamProgress(frame.payload, frame.type)

      if (frame.type === 'think') {
        target.thinks.push(frame.payload)
        bumpStreamPreview()
      } else if (frame.type === 'data') {
        target.content += frame.payload
        bumpStreamPreview()
      } else if (frame.type === 'event') {
        const payload = frame.payload || ''
        if (payload === 'Streaming finished') {
          streaming.value = false
          streamingMsgId.value = ''
          bumpStreamPreview()
          void loadHistory()
        } else if (payload.startsWith('error:')) {
          target.thinks.push(payload)
          bumpStreamPreview()
          streaming.value = false
          streamingMsgId.value = ''
          ElMessage.error(payload)
          void loadHistory()
        } else if (payload === 'History Record completed') {
          historyPage.value = 1
          void loadHistory()
        } else if (payload !== 'Connection established') {
          target.thinks.push(payload)
          bumpStreamPreview()
        }
      }
      void scrollToBottom()
    }

    try {
      await props.endpoint(
        {
          query: q,
          source_id: sourceId.value,
          source: props.source,
          pattern: currentPatternForRequest(),
          library: showLibrary.value ? selectedLibrary.value : '',
          sourceId: llmConfig.sourceId || undefined,
          model: llmConfig.model,
          type: llmConfig.type || undefined,
          baseUrl: llmConfig.baseUrl || undefined,
          apiKey: llmConfig.apiKey || undefined,
          temperature: Number(llmConfig.temperature || 0.3)
        },
        onFrame,
        { signal: abortController.signal }
      )
    } catch (e: any) {
      streaming.value = false
      streamingMsgId.value = ''
      ElMessage.error(e?.message || '请求失败')
      void loadHistory()
    } finally {
      streaming.value = false
      streamingMsgId.value = ''
    abortController = null
    resetStreamProgress()
  }
  }

  onMounted(async () => {
    handleNewSession()
    await Promise.all([loadSettings(), loadLibraries(), loadHistory()])
  })
</script>

<style scoped>
  .taixu-sse-chat {
    min-height: 0;
  }

  .chat-card {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .chat-card :deep(.el-card__body) {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
    flex-shrink: 0;
  }

  .stream-progress {
    flex: 1;
    min-width: 220px;
    max-width: 420px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .stream-stage {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .toolbar-left {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
  }

  .content {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 12px;
    overflow: hidden;
  }

  .chat-panel {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .side-panel {
    width: 360px;
    overflow: hidden;
    flex-shrink: 0;
  }

  .settings-readout {
    background: var(--el-fill-color-lighter);
    padding: 10px 12px;
    border-radius: 8px;
    margin-bottom: 14px;
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }

  .settings-row {
    display: flex;
    gap: 8px;
    margin-bottom: 6px;
  }

  .settings-label {
    flex-shrink: 0;
    width: 72px;
  }

  .settings-value {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--el-text-color-regular);
  }

  .settings-note {
    margin-top: 8px;
    font-size: 12px;
  }

  .history-toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 10px;
  }

  .history-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 10px;
  }

  .message-list {
    flex: 1;
    min-height: 0;
    overflow: auto;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 8px;
    padding: 12px;
    background: var(--el-bg-color);
  }

  .message-row {
    display: flex;
    width: 100%;
    margin-bottom: 14px;
  }

  .message-row.user {
    justify-content: flex-end;
  }

  .message-row.assistant {
    justify-content: flex-start;
  }

  .message-inner {
    max-width: 95%;
    min-width: 0;
  }

  .message-meta {
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .message-row.user .message-meta {
    justify-content: flex-end;
  }

  .role-label {
    font-weight: 600;
  }

  .user-bubble {
    padding: 10px 12px;
    border-radius: 8px;
    background: var(--el-color-primary-light-9);
    color: var(--el-text-color-primary);
    white-space: pre-wrap;
  }

  .assistant-bubble {
    padding: 8px 10px;
    border-radius: 8px;
    background: var(--el-fill-color-lighter);
  }

  .assistant-bubble :deep(.md-editor) {
    border: none;
    box-shadow: none;
  }

  .assistant-bubble :deep(.md-editor-preview-wrapper) {
    padding: 0;
  }

  .think-collapse {
    margin-bottom: 10px;
  }

  .think-content {
    display: flex;
    flex-direction: column;
    gap: 6px;
    color: var(--el-text-color-regular);
    font-size: 12px;
    white-space: pre-wrap;
  }

  .composer {
    flex-shrink: 0;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--el-border-color-lighter);
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }

  .composer-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
</style>
