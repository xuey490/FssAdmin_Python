<template>
  <div class="taixu-dialog-workbench art-full-height">
    <ElCard shadow="never" class="workbench-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <ElTag type="info">{{ title }}</ElTag>
          <ElSelect
            v-model="llmConfig.sourceId"
            style="width: 220px"
            placeholder="聊天模型"
            :disabled="streaming"
            @change="onLlmModelChange"
          >
            <ElOption v-for="m in chatModelOptions" :key="m.value" :label="m.label" :value="m.value" />
          </ElSelect>
          <ElButton :disabled="streaming" @click="createNewDialog">新会话</ElButton>
          <ElTag v-if="streaming" type="warning">生成中...</ElTag>
          <ElTag v-else type="success">就绪</ElTag>
        </div>
        <div class="toolbar-right">
          <ElButton v-if="streaming" type="warning" @click="stopStreaming">停止</ElButton>
        </div>
      </div>

      <div class="content">
        <div class="chat-panel">
          <div ref="messageListRef" class="message-list">
            <div v-if="messages.length === 0" class="empty-tip">请选择历史对话或新建会话</div>
            <div v-for="msg in messages" :key="msg.id" class="message-row" :class="msg.role">
              <div class="message-inner">
                <div class="message-meta">
                  <span class="role-label">{{ msg.role === 'user' ? '我' : 'AI' }}</span>
                </div>
                <div v-if="msg.role === 'user'" class="user-bubble">{{ msg.content }}</div>
                <div v-else class="assistant-bubble">
                  <ElCollapse v-if="msg.think" class="think-collapse">
                    <ElCollapseItem title="思考过程" name="think">
                      <MdPreview
                        :model-value="msg.think"
                        preview-theme="github"
                        :theme="previewTheme"
                        :code-theme="codeTheme"
                        class="think-md-preview"
                      />
                    </ElCollapseItem>
                  </ElCollapse>
                  <MdPreview
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
              :disabled="streaming || !currentDialogId"
              @keydown.enter.exact.prevent="handleSend"
            />
            <div class="composer-actions">
              <ElButton
                type="primary"
                :loading="streaming"
                :disabled="!inputText.trim() || streaming || !currentDialogId"
                @click="handleSend"
              >
                发送
              </ElButton>
            </div>
          </div>
        </div>

        <div class="side-panel">
          <ElTabs v-model="activeTab">
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
                height="520"
                border
                :data="historyList"
                highlight-current-row
                @current-change="handleSelectHistory"
              >
                <ElTableColumn label="标题" min-width="160" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span :title="row.name">{{ truncateHistoryTitle(row.name) }}</span>
                  </template>
                </ElTableColumn>
                <ElTableColumn label="操作" width="80" align="center">
                  <template #default="{ row }">
                    <ElButton
                      link
                      type="primary"
                      :icon="EditPen"
                      title="重命名"
                      @click.stop="renameDialog(row)"
                    />
                    <ElButton
                      link
                      type="danger"
                      :icon="Delete"
                      title="删除"
                      @click.stop="deleteDialog(row)"
                    />
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
    fetchTaixuHistoryRecords,
    fetchTaixuModelList,
    fetchTaixuMemoryDetails,
    fetchTaixuSettingDetail,
    updateTaixuHistory,
    type TaixuHistoryPageResult,
    type TaixuModelItem,
    type TaixuSseFrame
  } from '@/api/taixu'

  export interface EndpointFn {
    (body: Record<string, any>, onFrame: (frame: TaixuSseFrame) => void, options?: { signal?: AbortSignal }): Promise<void>
  }

  interface ChatMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    think: string
  }

  interface LlmConnectConfig {
    sourceId: string
    model: string
    type: string
    baseUrl: string
    apiKey: string
    temperature: string
  }

  interface HistoryRow {
    id: string
    name: string
    source: string
    pattern: string
    create_time: string
    chat_model_id?: string
  }

  const props = defineProps<{
    title: string
    source: string
    pattern: string
    endpoint: EndpointFn
  }>()

  const settingStore = useSettingStore()
  const previewTheme = computed(() => (settingStore.isDark ? 'dark' : 'light'))
  const codeTheme = computed(() => (settingStore.isDark ? 'github-dark' : 'github'))

  const activeTab = ref('history')
  const historyKeyword = ref('')
  const loadingHistory = ref(false)
  const historyList = ref<HistoryRow[]>([])
  const historyPage = ref(1)
  const historyPageSize = ref(10)
  const historyTotal = ref(0)
  const currentDialogId = ref('')
  const llmModels = ref<TaixuModelItem[]>([])
  const chatModelOptions = ref<Array<{ label: string; value: string }>>([])
  const llmConfig = reactive<LlmConnectConfig>({
    sourceId: '',
    model: '',
    type: '',
    baseUrl: '',
    apiKey: '',
    temperature: '0.3'
  })

  const inputText = ref('')
  const messages = ref<ChatMessage[]>([])
  const streaming = ref(false)
  const streamingMsgId = ref('')
  const messageListRef = ref<HTMLElement>()
  let abortController: AbortController | null = null

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

  const normalizeHistoryResult = (res: TaixuHistoryPageResult | HistoryRow[] | null | undefined) => {
    if (Array.isArray(res)) {
      historyTotal.value = res.length
      return res as HistoryRow[]
    }
    const page = res as TaixuHistoryPageResult | undefined
    historyTotal.value = Number(page?.total ?? 0)
    return (page?.records || []) as HistoryRow[]
  }

  const searchHistory = async () => {
    historyPage.value = 1
    await loadHistory()
  }

  const onHistoryPageSizeChange = async () => {
    historyPage.value = 1
    await loadHistory()
  }

  const createNewDialog = () => {
    stopStreaming()
    currentDialogId.value = newId()
    messages.value = [
      { id: newId(), role: 'assistant', content: '你好！我是LLM智能对话助手。', think: '' }
    ]
    inputText.value = ''
    void scrollToBottom()
  }

  const stopStreaming = () => {
    abortController?.abort()
    abortController = null
    streaming.value = false
    streamingMsgId.value = ''
  }

  const loadHistory = async () => {
    loadingHistory.value = true
    try {
      const res = await fetchTaixuHistoryRecords({
        source: props.source,
        pattern: props.pattern,
        name: historyKeyword.value.trim() || undefined,
        current_page: historyPage.value,
        page_size: historyPageSize.value
      })
      historyList.value = normalizeHistoryResult(res)
    } finally {
      loadingHistory.value = false
    }
  }

  const formatModelLabel = (m: TaixuModelItem) => {
    const name = m.display_name || m.model_name || m.model_id || m.id
    return `${name}${m.source ? ` (${m.source})` : ''}`
  }

  const applyModelRow = (model: TaixuModelItem) => {
    llmConfig.sourceId = model.id
    // ponytail: OpenAI-compatible providers like Volcengine Ark require endpoint/model_id first
    llmConfig.model = model.model_id || model.model_name || model.display_name || ''
    llmConfig.type = model.source || ''
    llmConfig.baseUrl = model.base_url || ''
    llmConfig.apiKey = model.api_key || ''
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

    if (llmConfig.sourceId) {
      const matched = llmModels.value.find((m) => m.id === llmConfig.sourceId)
      if (matched) applyModelRow(matched)
      else if (raw.model) llmConfig.model = normalizeSettingModel(String(raw.model), llmConfig.type)
    }
  }

  const onLlmModelChange = (sourceId: string) => {
    const model = llmModels.value.find((m) => m.id === sourceId)
    if (model) applyModelRow(model)
  }

  const loadLlmConfig = async () => {
    const [models, setting] = await Promise.all([
      fetchTaixuModelList({ type: 'llm' }),
      fetchTaixuSettingDetail('llm')
    ])
    llmModels.value = Array.isArray(models) ? models : []
    chatModelOptions.value = llmModels.value.map((m) => ({
      label: formatModelLabel(m),
      value: m.id
    }))
    applyLlmSettingContent((setting?.content ?? setting ?? {}) as Record<string, any>)
    if (!llmConfig.sourceId && llmModels.value.length) {
      applyModelRow(llmModels.value[0])
    }
  }

  const handleSelectHistory = async (row: HistoryRow) => {
    if (!row?.id) return
    stopStreaming()
    currentDialogId.value = row.id
    const details = await fetchTaixuMemoryDetails({ source_id: row.id })
    const list = (details || []) as Array<{ id: string; type: string; content: string }>
    const mapped: ChatMessage[] = [
      { id: newId(), role: 'assistant', content: '已加载历史对话。', think: '' }
    ]
    for (const item of list) {
      const role = item.type === 'user' ? 'user' : 'assistant'
      mapped.push({ id: item.id || newId(), role, content: item.content || '', think: '' })
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
    if (currentDialogId.value === row.id) {
      createNewDialog()
    }
    await loadHistory()
  }

  const handleSend = async () => {
    const q = inputText.value.trim()
    if (!q || streaming.value || !currentDialogId.value) return
    if (!llmConfig.model) {
      ElMessage.warning('请先在设置管理配置文本模型，或选择可用模型')
      return
    }

    streaming.value = true
    streamingMsgId.value = ''
    abortController?.abort()
    abortController = new AbortController()

    const userMsg: ChatMessage = { id: newId(), role: 'user', content: q, think: '' }
    const aiMsg: ChatMessage = { id: newId(), role: 'assistant', content: '', think: '' }
    streamingMsgId.value = aiMsg.id
    messages.value = [...messages.value, userMsg, aiMsg]
    inputText.value = ''
    await scrollToBottom()

    // Always look up through messages.value so mutations go through Vue's reactive proxy
    const getTarget = () => messages.value.find((m) => m.id === aiMsg.id)

    const onFrame = (frame: TaixuSseFrame) => {
      const target = getTarget()
      if (!target) return

      if (frame.type === 'data') {
        target.content += frame.payload
      } else if (frame.type === 'think') {
        target.think += frame.payload
      } else if (frame.type === 'event') {
        const payload = frame.payload || ''
        if (payload === 'Streaming finished') {
          streaming.value = false
          streamingMsgId.value = ''
          void loadHistory()
        } else if (payload.startsWith('error:')) {
          target.think = target.think ? `${target.think}\n${payload}` : payload
          streaming.value = false
          streamingMsgId.value = ''
          ElMessage.error(payload)
          void loadHistory()
        } else if (payload === 'History Record completed') {
          historyPage.value = 1
          void loadHistory()
        } else if (payload !== 'Connection established') {
          target.think = target.think ? `${target.think}\n${payload}` : payload
        }
      }
      void scrollToBottom()
    }

    try {
      await props.endpoint(
        {
          query: q,
          source_id: currentDialogId.value,
          source: props.source,
          pattern: props.pattern,
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
    }
  }

  onMounted(async () => {
    createNewDialog()
    await loadLlmConfig()
    await loadHistory()
  })
</script>

<style scoped>
  .taixu-dialog-workbench {
    min-height: 0;
  }

  .workbench-card {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .workbench-card :deep(.el-card__body) {
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
    width: 560px;
    overflow: hidden;
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
    overflow-x: hidden;
    overflow-y: auto;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 8px;
    padding: 12px;
    background: var(--el-bg-color);
    display: flex;
    flex-direction: column;
  }

  .empty-tip {
    padding: 24px;
    color: var(--el-text-color-secondary);
    text-align: center;
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
    min-width: 0%;
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
    max-width: 100%;
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

  .assistant-bubble :deep(.md-editor-preview) {
    background: transparent;
    font-size: 14px;
    line-height: 1.6;
  }

  .assistant-bubble :deep(pre) {
    margin: 8px 0;
    border-radius: 6px;
    overflow: auto;
  }

  .think-collapse {
    margin-bottom: 10px;
  }

  .think-md-preview :deep(.md-editor-preview) {
    font-size: 12px;
    color: var(--el-text-color-regular);
  }

  .composer {
    flex-shrink: 0;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--el-border-color-lighter);
    display: flex;
    gap: 10px;
    align-items: flex-start;
    background: var(--el-bg-color);
  }

  .composer-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
</style>
