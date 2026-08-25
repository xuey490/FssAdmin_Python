<template>
  <div class="ai-chat-page art-full-height">
    <ElCard shadow="never" class="chat-card">
      <div class="chat-layout">
        <aside class="session-panel">
          <div class="panel-head">
            <span>会话</span>
            <ElButton size="small" type="primary" :loading="creating" @click="handleNewSession">
              新建
            </ElButton>
          </div>
          <div v-if="sessions.length === 0" class="empty-tip">暂无会话，点击新建开始</div>
          <div
            v-for="item in sessions"
            :key="item.session_uuid"
            class="session-item"
            :class="{ active: item.session_uuid === currentSessionUuid }"
            @click="selectSession(item.session_uuid)"
          >
            <div class="session-body">
              <div class="session-title">{{ item.title }}</div>
              <div class="session-meta">{{ item.message_count }} 条</div>
            </div>
            <div class="session-actions" @click.stop>
              <ElButton
                link
                type="primary"
                :icon="EditPen"
                title="编辑标题"
                @click="handleEditTitle(item)"
              />
              <ElButton
                link
                type="danger"
                :icon="Delete"
                title="删除对话"
                @click="handleDeleteSession(item)"
              />
            </div>
          </div>
        </aside>

        <section class="chat-panel">
          <div class="chat-toolbar">
            <ElSelect
              v-model="selectedModelId"
              placeholder="选择模型"
              style="width: 220px"
              :disabled="!currentSessionUuid"
              @change="handleModelChange"
            >
              <ElOption
                v-for="m in modelOptions"
                :key="m.id"
                :label="`${m.name} (${m.provider_name})`"
                :value="m.id"
              />
            </ElSelect>
            <ElTag v-if="streaming" type="warning">生成中...</ElTag>
            <ElTag v-else-if="ws.connecting.value" type="warning">连接中...</ElTag>
            <ElTag v-else-if="wsConnected" type="success">已连接</ElTag>
            <ElTag v-else type="danger" :title="ws.lastError.value">{{ ws.lastError.value || '未连接' }}</ElTag>
            <ElButton v-if="!wsConnected && !ws.connecting.value" size="small" @click="connectWs">重连</ElButton>
          </div>

          <div v-if="currentSessionUuid && sessionStats" class="chat-stats-bar">
            <span>会话 tokens <b>{{ formatNum(sessionStats.total_tokens) }}</b></span>
            <span v-if="sessionStats.turn_tokens != null">
              本次 tokens <b>{{ formatNum(sessionStats.turn_tokens) }}</b>
            </span>
            <span v-if="sessionStats.cache_hit_rate != null">
              缓存命中 <b>{{ sessionStats.cache_hit_rate }}%</b>
            </span>
            <span v-else-if="sessionStats.turn_tokens != null" class="muted">缓存命中 —</span>
            <span>当前会话 <b>{{ sessionStats.rounds }} 轮</b></span>
            <span>
              上下文
              <b :class="{ warn: (sessionStats.context_ratio ?? 0) >= sessionStats.compact_threshold * 0.5 }">
                {{ sessionStats.context_ratio ?? 0 }}%
              </b>
            </span>
            <span class="muted">压缩阈值 {{ sessionStats.compact_threshold }}%</span>
          </div>

          <div ref="messageListRef" class="message-list">
            <div v-if="!currentSessionUuid" class="empty-tip">请先创建或选择会话</div>
            <div
              v-for="msg in messages"
              :key="msg.message_uuid"
              class="message-row"
              :class="msg.role"
            >
              <div class="message-meta">
                <span class="role-label">{{ msg.role === 'user' ? '我' : 'AI' }}</span>
                <span v-if="msg.model_name" class="model-badge">{{ msg.model_name }}</span>
              </div>
              <div v-if="msg.role === 'user'" class="user-bubble">{{ msg.content }}</div>
              <div v-else class="assistant-bubble">
                <MdPreview
                  :model-value="msg.content || (msg.status === 'streaming' ? '...' : '')"
                  preview-theme="github"
                  :theme="previewTheme"
                  code-theme="github"
                />
              </div>
            </div>
          </div>

          <div class="composer">
            <ElInput
              v-model="inputText"
              type="textarea"
              :rows="3"
              placeholder="输入消息，Enter 发送（Shift+Enter 换行）"
              :disabled="!currentSessionUuid || streaming"
              @keydown.enter.exact.prevent="handleSend"
            />
            <div class="composer-actions">
              <ElButton
                v-if="streaming"
                type="warning"
                @click="handleStop"
              >
                停止
              </ElButton>
              <ElButton
                type="primary"
                :loading="streaming"
                :disabled="!inputText.trim() || !currentSessionUuid"
                @click="handleSend"
              >
                发送
              </ElButton>
            </div>
          </div>
        </section>
      </div>
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
  import { MdPreview } from 'md-editor-v3'
  import 'md-editor-v3/lib/style.css'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { Delete, EditPen } from '@element-plus/icons-vue'
  import { useUserStore } from '@/store/modules/user'
  import { useSettingStore } from '@/store/modules/setting'
  import { useAiChatWs } from '@/composables/useAiChatWs'
  import {
    fetchAiMessages,
    fetchAiModelOptions,
    fetchAiSessions,
    fetchCreateAiSession,
    fetchUpdateSessionModel,
    fetchUpdateSessionTitle,
    fetchDeleteAiSession,
    type AiMessageItem,
    type AiModelOption,
    type AiSessionItem,
    type AiSessionStats
  } from '@/api/ai'

  defineOptions({ name: 'AiChatPage' })

  const userStore = useUserStore()
  const settingStore = useSettingStore()
  const previewTheme = computed(() => (settingStore.isDark ? 'dark' : 'light'))

  const ws = useAiChatWs()
  const wsConnected = computed(() => ws.connected.value && ws.authed.value)

  const sessions = ref<AiSessionItem[]>([])
  const messages = ref<AiMessageItem[]>([])
  const modelOptions = ref<AiModelOption[]>([])
  const currentSessionUuid = ref('')
  const selectedModelId = ref('')
  const inputText = ref('')
  const creating = ref(false)
  const streaming = ref(false)
  const streamingMessageUuid = ref('')
  const messageListRef = ref<HTMLElement>()
  const sessionStats = ref<AiSessionStats | null>(null)

  const formatNum = (n: number) => (n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : `${n}`)

  const scrollToBottom = async () => {
    await nextTick()
    const el = messageListRef.value
    if (el) el.scrollTop = el.scrollHeight
  }

  const loadModels = async () => {
    const res = await fetchAiModelOptions()
    modelOptions.value = res.list || []
    if (!selectedModelId.value) {
      selectedModelId.value =
        modelOptions.value.find((m) => m.is_default)?.id || modelOptions.value[0]?.id || ''
    }
  }

  const loadSessions = async () => {
    const res = await fetchAiSessions({ page: 1, limit: 50 })
    sessions.value = res.list || []
  }

  const loadMessages = async (sessionUuid: string) => {
    const res = await fetchAiMessages(sessionUuid)
    messages.value = (res.list || []) as AiMessageItem[]
    selectedModelId.value = res.default_model_id || selectedModelId.value
    sessionStats.value = res.stats
      ? { ...res.stats }
      : null
    await scrollToBottom()
  }

  const selectSession = async (sessionUuid: string) => {
    currentSessionUuid.value = sessionUuid
    await loadMessages(sessionUuid)
  }

  const handleNewSession = async () => {
    creating.value = true
    try {
      const res = await fetchCreateAiSession({ model_id: selectedModelId.value || undefined })
      await loadSessions()
      currentSessionUuid.value = res.session_uuid
      selectedModelId.value = res.default_model_id
      messages.value = []
      sessionStats.value = null
      ElMessage.success('已创建新会话')
    } finally {
      creating.value = false
    }
  }

  const handleModelChange = async (modelId: string) => {
    if (!currentSessionUuid.value || !modelId) return
    await fetchUpdateSessionModel(currentSessionUuid.value, modelId)
    ElMessage.success('已切换模型')
  }

  const handleEditTitle = async (item: AiSessionItem) => {
    try {
      const { value } = await ElMessageBox.prompt('请输入新的对话标题', '编辑标题', {
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        inputValue: item.title,
        inputPattern: /\S+/,
        inputErrorMessage: '标题不能为空'
      })
      const title = value.trim()
      await fetchUpdateSessionTitle(item.session_uuid, title)
      item.title = title
      ElMessage.success('标题已更新')
    } catch {
      // 用户取消
    }
  }

  const handleDeleteSession = async (item: AiSessionItem) => {
    try {
      await ElMessageBox.confirm('删除后将无法恢复该对话及全部历史消息，确定继续？', '删除对话', {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      })
    } catch {
      return
    }

    await fetchDeleteAiSession(item.session_uuid)
    sessions.value = sessions.value.filter((s) => s.session_uuid !== item.session_uuid)

    if (currentSessionUuid.value === item.session_uuid) {
      if (sessions.value.length) {
        await selectSession(sessions.value[0].session_uuid)
      } else {
        currentSessionUuid.value = ''
        messages.value = []
        sessionStats.value = null
      }
    }
    ElMessage.success('对话已删除')
  }

  const ensureWs = async () => {
    const token = userStore.accessToken
    if (!token) throw new Error('未登录')
    await ws.connect(token)
  }

  const connectWs = async () => {
    try {
      await ensureWs()
    } catch (e: any) {
      ElMessage.error(e?.message || 'WebSocket 连接失败')
    }
  }

  const handleSend = async () => {
    const content = inputText.value.trim()
    if (!content || !currentSessionUuid.value || streaming.value) return

    try {
      await ensureWs()
    } catch (e: any) {
      ElMessage.error(e?.message || 'WebSocket 连接失败')
      return
    }

    inputText.value = ''
    streaming.value = true

    ws.chatSend({
      session_uuid: currentSessionUuid.value,
      content,
      model_id: selectedModelId.value || undefined
    })
  }

  const handleStop = () => {
    if (!currentSessionUuid.value || !streaming.value) return
    ws.chatStop({
      session_uuid: currentSessionUuid.value,
      message_uuid: streamingMessageUuid.value || undefined
    })
    streaming.value = false
  }

  onMounted(async () => {
    await loadModels()
    await loadSessions()
    if (sessions.value.length) {
      await selectSession(sessions.value[0].session_uuid)
    }

    // 进入页面自动连接 WebSocket（与 HTTP 同端口，无需单独启动 WS 服务）
    await connectWs()

    ws.on('chat.user_message', (data: any) => {
      messages.value.push({
        message_uuid: data.message_uuid,
        role: 'user',
        content: data.content,
        status: 'completed',
        model_id: null,
        model_name: null,
        provider_name: null,
        create_time: new Date().toISOString()
      })
      scrollToBottom()
    })

    ws.on('chat.message_start', (data: any) => {
      streamingMessageUuid.value = data.message_uuid
      messages.value.push({
        message_uuid: data.message_uuid,
        role: 'assistant',
        content: '',
        status: 'streaming',
        model_id: data.model_id,
        model_name: data.model_name,
        provider_name: data.provider_name,
        create_time: new Date().toISOString()
      })
      scrollToBottom()
    })

    ws.on('chat.token', (data: any) => {
      const target = messages.value.find((m) => m.message_uuid === data.message_uuid)
      if (target) {
        target.content += data.delta
        scrollToBottom()
      }
    })

    ws.on('chat.message_done', (data: any) => {
      const target = messages.value.find((m) => m.message_uuid === data.message_uuid)
      if (target) {
        target.content = data.content
        target.status = 'completed'
      }
      streaming.value = false
      streamingMessageUuid.value = ''
      if (data.session_stats && data.context) {
        sessionStats.value = {
          total_tokens: data.session_stats.total_tokens,
          rounds: data.session_stats.rounds,
          context_window: data.context.context_window,
          compact_threshold: data.context.compact_threshold,
          turn_tokens: data.usage?.total_tokens,
          turn_prompt_tokens: data.usage?.prompt_tokens,
          cache_hit_rate: data.session_stats.cache_hit_rate,
          context_ratio: data.context.ratio
        }
      }
      loadSessions()
      scrollToBottom()
    })

    ws.on('chat.error', (data: any) => {
      streaming.value = false
      streamingMessageUuid.value = ''
      ElMessage.error(data?.message || '对话失败')
    })
  })

  onUnmounted(() => {
    ws.disconnect()
  })

  watch(
    () => userStore.accessToken,
    () => ws.disconnect()
  )
</script>

<style scoped>
  .ai-chat-page {
    padding: 12px;
  }

  .chat-card {
    height: calc(100vh - 120px);
  }

  .chat-card :deep(.el-card__body) {
    height: 100%;
    padding: 0;
  }

  .chat-layout {
    display: flex;
    height: 100%;
    min-height: 560px;
  }

  .session-panel {
    width: 240px;
    border-right: 1px solid var(--el-border-color-light);
    display: flex;
    flex-direction: column;
  }

  .panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    font-weight: 600;
  }

  .session-item {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 10px 8px 10px 12px;
    cursor: pointer;
    border-bottom: 1px solid var(--el-border-color-extra-light);
  }

  .session-item:hover,
  .session-item.active {
    background: var(--el-fill-color-light);
  }

  .session-body {
    flex: 1;
    min-width: 0;
  }

  .session-actions {
    display: none;
    flex-shrink: 0;
    align-items: center;
  }

  .session-item:hover .session-actions {
    display: flex;
  }

  .session-actions :deep(.el-button) {
    padding: 4px;
    margin: 0;
  }

  .session-title {
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .session-meta {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 4px;
  }

  .chat-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .chat-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  .chat-stats-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 16px;
    padding: 6px 12px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    border-bottom: 1px solid var(--el-border-color-extra-light);
    background: var(--el-fill-color-blank);
  }

  .chat-stats-bar b {
    color: var(--el-text-color-primary);
    font-weight: 600;
    margin-left: 2px;
  }

  .chat-stats-bar b.warn {
    color: var(--el-color-warning);
  }

  .chat-stats-bar .muted {
    color: var(--el-text-color-placeholder);
  }

  .message-list {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    background: var(--el-fill-color-blank);
  }

  .message-row {
    margin-bottom: 16px;
  }

  .message-row.user {
    text-align: right;
  }

  .message-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .message-row.user .message-meta {
    justify-content: flex-end;
  }

  .model-badge {
    background: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
    padding: 0 6px;
    border-radius: 4px;
  }

  .user-bubble {
    display: inline-block;
    max-width: 80%;
    text-align: left;
    background: var(--el-color-primary);
    color: #fff;
    padding: 10px 12px;
    border-radius: 10px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .assistant-bubble {
    max-width: 90%;
    background: var(--el-fill-color-light);
    border-radius: 10px;
    padding: 8px 10px;
  }

  .assistant-bubble :deep(.md-editor-preview) {
    background: transparent;
  }

  .composer {
    border-top: 1px solid var(--el-border-color-lighter);
    padding: 12px;
  }

  .composer-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 8px;
  }

  .empty-tip {
    padding: 24px;
    text-align: center;
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }
</style>
