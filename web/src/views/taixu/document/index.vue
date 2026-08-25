<template>
  <div class="art-full-height">
    <ElCard class="art-table-card" shadow="never">
      <ArtTableHeader v-model:columns="columnChecks" :loading="loading" @refresh="refreshData">
        <template #left>
          <ElUpload
            :show-file-list="false"
            :auto-upload="true"
            :http-request="handleUpload"
            :disabled="uploading"
          >
            <ElButton type="primary" :loading="uploading" v-ripple>上传文件</ElButton>
          </ElUpload>
          <ElButton @click="showWebsiteDialog = true">站点入库</ElButton>
        </template>
        <template #right>
          <ElTag :type="queuePaused ? 'warning' : queueRunning ? 'success' : 'info'">
            {{ queuePaused ? '队列已暂停' : queueRunning ? `队列运行中(${queueLength})` : `队列待机(${queueLength})` }}
          </ElTag>
          <ElTag :type="queueHealth.worker_connected ? 'success' : 'danger'" :title="queueHealthTitle">
            {{ queueHealth.worker_connected ? '连接正常' : '连接异常' }} · 最近消费
            {{ formatQueueTime(queueHealth.last_consumed_at) }}
          </ElTag>
          <ElButton
            size="small"
            :type="queuePaused ? 'success' : 'warning'"
            :loading="queueSwitching"
            @click="handleToggleQueue"
          >
            {{ queuePaused ? '恢复队列' : '暂停队列' }}
          </ElButton>
        </template>
      </ArtTableHeader>

      <ArtTable
        row-key="id"
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      >
        <template #index_status="{ row }">
          <div v-if="isIndexing(row)" class="index-cell">
            <ElProgress
              :percentage="Number(row.index_progress || 0)"
              :stroke-width="8"
              :status="row.index_status === 'failed' ? 'exception' : undefined"
            />
            <span class="index-msg">{{ row.index_message || indexStageLabel(row.index_status) }}</span>
          </div>
          <div v-else-if="row.index_status === 'pending'" class="index-cell">
            <ElProgress :percentage="0" :stroke-width="8" :indeterminate="true" />
            <span class="index-msg">{{ row.index_message || '等待入库分析' }}</span>
          </div>
          <ElTag v-else-if="row.index_status === 'failed'" type="danger" :title="row.index_message">
            {{ row.index_message || '入库失败' }}
          </ElTag>
          <ElTag v-else type="success">已就绪</ElTag>
        </template>
        <template #operation="{ row }">
          <div class="flex gap-2 items-center">
            <ElButton
              v-if="canReindex(row)"
              size="small"
              type="warning"
              plain
              :disabled="isIndexing(row)"
              @click="handleReindex(row)"
            >
              重跑
            </ElButton>
            <SaButton type="secondary" :disabled="isIndexing(row)" @click="handlePreview(row)" />
            <SaButton type="primary" @click="handleDownload(row)" />
            <SaButton type="error" @click="handleDelete(row)" />
          </div>
        </template>
      </ArtTable>
    </ElCard>

    <ElDialog v-model="previewVisible" title="预览" width="860px" align-center>
      <MdPreview
        :model-value="previewText"
        preview-theme="github"
        :theme="previewTheme"
        code-theme="github"
      />
    </ElDialog>

    <ElDialog v-model="showWebsiteDialog" title="站点入库" width="560px" align-center>
      <ElForm label-width="100px">
        <ElFormItem label="URL">
          <ElInput v-model="websiteUrl" placeholder="https://example.com" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="showWebsiteDialog = false">取消</ElButton>
        <ElButton type="primary" :loading="uploadingWebsite" @click="handleWebsite">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { MdPreview } from 'md-editor-v3'
  import 'md-editor-v3/lib/style.css'
  import { useSettingStore } from '@/store/modules/setting'
  import { useTable } from '@/hooks/core/useTable'
  import {
    deleteTaixuDocuments,
    downloadTaixuDocument,
    fetchTaixuDocumentQueueHealth,
    fetchTaixuDocumentIndexStatus,
    fetchTaixuDocumentQueueStatus,
    fetchTaixuDocuments,
    pauseTaixuDocumentQueue,
    previewTaixuDocument,
    reindexTaixuDocuments,
    resumeTaixuDocumentQueue,
    uploadTaixuDocument,
    uploadTaixuWebsite,
    type TaixuDocumentItem,
    type TaixuDocumentQueueHealth
  } from '@/api/taixu'

  defineOptions({ name: 'TaixuDocumentPage' })

  const settingStore = useSettingStore()
  const previewTheme = computed(() => (settingStore.isDark ? 'dark' : 'light'))

  const INDEXING = new Set(['queued', 'extract', 'split', 'vector', 'graph'])

  const indexStageLabel = (status?: string) => {
    const map: Record<string, string> = {
      queued: '排队中',
      extract: '解析文档',
      split: '文本分块',
      vector: '写入向量库',
      graph: '写入知识图谱'
    }
    return map[String(status || '')] || String(status || '')
  }

  const isIndexing = (row: Record<string, any>) => INDEXING.has(String(row.index_status || ''))

  const canReindex = (row: Record<string, any>) => {
    const status = String(row.index_status || '')
    return status === 'failed' || status === 'pending'
  }

  const {
    columns,
    columnChecks,
    data,
    loading,
    pagination,
    handleSizeChange,
    handleCurrentChange,
    refreshData
  } = useTable({
    core: {
      apiFn: fetchTaixuDocuments,
      paginationKey: { current: 'current_page', size: 'page_size' },
      columnsFactory: () => [
        { prop: 'document_name', label: '文档名', minWidth: 220 },
        { prop: 'document_type', label: '类型', width: 90 },
        { prop: 'document_size', label: '大小(MB)', width: 100 },
        { prop: 'library_number', label: '库编号', minWidth: 140 },
        { prop: 'index_status', label: '入库进度', minWidth: 200, useSlot: true },
        { prop: 'upload_time', label: '上传时间', width: 170 },
        { prop: 'operation', label: '操作', width: 260, fixed: 'right', useSlot: true }
      ]
    }
  })

  const previewVisible = ref(false)
  const previewText = ref('')
  const showWebsiteDialog = ref(false)
  const websiteUrl = ref('')
  const uploading = ref(false)
  const uploadingWebsite = ref(false)
  const pendingIds = ref<string[]>([])
  const queuePaused = ref(false)
  const queueRunning = ref(false)
  const queueLength = ref(0)
  const queueHealth = ref<TaixuDocumentQueueHealth>({
    worker_connected: false,
    worker_status: 'unknown',
    last_consumed_at: null,
    last_error_at: null,
    last_error_message: null
  })
  const queueSwitching = ref(false)
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let queueStatusTimer: ReturnType<typeof setInterval> | null = null

  const formatQueueTime = (ts?: number | null) => {
    if (!ts) return '-'
    const d = new Date(ts)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  }

  const queueHealthTitle = computed(() => {
    const h = queueHealth.value
    return [
      `连接状态: ${h.worker_connected ? '正常' : '异常'} (${h.worker_status || 'unknown'})`,
      `最近消费: ${formatQueueTime(h.last_consumed_at)}`,
      `最近错误: ${h.last_error_message || '-'}`
    ].join('\n')
  })

  const mergeIndexStatus = (rows: TaixuDocumentItem[], jobs: any[]) => {
    const map = new Map(jobs.map((j) => [j.documentId, j]))
    for (const row of rows as any[]) {
      const job = map.get(row.id)
      if (job) {
        row.index_status = job.status
        row.index_progress = job.progress
        row.index_message = job.message
      }
    }
  }

  const syncPendingFromTable = () => {
    const ids = (data.value as TaixuDocumentItem[])
      .filter((row) => isIndexing(row) || row.index_status === 'pending')
      .map((row) => row.id)
    pendingIds.value = [...new Set([...pendingIds.value, ...ids])].filter(Boolean)
  }

  const pollIndexStatus = async () => {
    syncPendingFromTable()
    if (!pendingIds.value.length) return
    const jobs = await fetchTaixuDocumentIndexStatus(pendingIds.value)
    const list = Array.isArray(jobs) ? jobs : []
    mergeIndexStatus(data.value as TaixuDocumentItem[], list)
    pendingIds.value = pendingIds.value.filter((id) => {
      const job = list.find((j) => j.documentId === id)
      if (!job) {
        const row = (data.value as TaixuDocumentItem[]).find((r) => r.id === id)
        return row ? isIndexing(row) : false
      }
      return INDEXING.has(String(job.status))
    })
    if (!pendingIds.value.length) await refreshData()
  }

  const trackUploaded = (res: { id?: string; index_status?: string }) => {
    const id = res?.id
    if (!id) return
    pendingIds.value = [...new Set([...pendingIds.value, String(id)])]
    const row = (data.value as TaixuDocumentItem[]).find((r) => r.id === id)
    if (row) {
      row.index_status = res.index_status || 'queued'
      row.index_progress = 0
      row.index_message = '排队中'
    }
  }

  const loadQueueStatus = async () => {
    try {
      const status = await fetchTaixuDocumentQueueStatus()
      queuePaused.value = Boolean(status?.paused)
      queueRunning.value = Boolean(status?.running)
      queueLength.value = Number(status?.queue_length || 0)
    } catch (e: any) {
      ElMessage.error(e?.message || '加载队列状态失败')
    }
  }

  const loadQueueHealth = async () => {
    try {
      const health = await fetchTaixuDocumentQueueHealth()
      queueHealth.value = {
        worker_connected: Boolean(health?.worker_connected),
        worker_status: String(health?.worker_status || 'unknown'),
        last_consumed_at: health?.last_consumed_at ?? null,
        last_error_at: health?.last_error_at ?? null,
        last_error_message: health?.last_error_message ?? null
      }
    } catch {
      // Ignore transient health fetch errors to avoid UI noise
    }
  }

  const handleToggleQueue = async () => {
    queueSwitching.value = true
    try {
      const status = queuePaused.value ? await resumeTaixuDocumentQueue() : await pauseTaixuDocumentQueue()
      queuePaused.value = Boolean(status?.paused)
      queueRunning.value = Boolean(status?.running)
      queueLength.value = Number(status?.queue_length || 0)
      ElMessage.success(queuePaused.value ? '文档分析队列已暂停' : '文档分析队列已恢复')
    } catch (e: any) {
      ElMessage.error(e?.message || '队列操作失败')
    } finally {
      queueSwitching.value = false
    }
  }

  const handleUpload = async (options: any) => {
    const file = options?.file as File
    if (!file) return
    uploading.value = true
    try {
      const res = await uploadTaixuDocument(file)
      trackUploaded(res)
      ElMessage.success('上传成功，正在后台索引')
      await refreshData()
      await pollIndexStatus()
    } finally {
      uploading.value = false
    }
  }

  const handleWebsite = async () => {
    const url = websiteUrl.value.trim()
    if (!url) return
    uploadingWebsite.value = true
    try {
      const res = await uploadTaixuWebsite(url)
      trackUploaded(res)
      ElMessage.success('上传成功，正在后台索引')
      showWebsiteDialog.value = false
      websiteUrl.value = ''
      await refreshData()
      await pollIndexStatus()
    } finally {
      uploadingWebsite.value = false
    }
  }

  const handleReindex = async (row: Record<string, any>) => {
    await reindexTaixuDocuments({ ids: String(row.id) })
    pendingIds.value = [...new Set([...pendingIds.value, String(row.id)])]
    const target = (data.value as TaixuDocumentItem[]).find((r) => r.id === row.id)
    if (target) {
      target.index_status = 'queued'
      target.index_progress = 0
      target.index_message = '排队中'
    }
    ElMessage.success('已加入入库队列')
    await pollIndexStatus()
  }

  const handlePreview = async (row: Record<string, any>) => {
    const text = await previewTaixuDocument({
      documentName: row.document_name,
      documentType: row.document_type
    })
    previewText.value = typeof text === 'string' ? text : JSON.stringify(text, null, 2)
    previewVisible.value = true
  }

  const handleDownload = async (row: Record<string, any>) => {
    const blob = await downloadTaixuDocument({ documentName: row.document_name })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.document_name
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  const handleDelete = async (row: Record<string, any>) => {
    await ElMessageBox.confirm('确定删除该文档吗？（会同步清理向量库/图谱）', '删除', { type: 'warning' })
    await deleteTaixuDocuments({ ids: String(row.id) })
    pendingIds.value = pendingIds.value.filter((id) => id !== row.id)
    ElMessage.success('删除成功')
    await refreshData()
  }

  onMounted(() => {
    void loadQueueStatus()
    void loadQueueHealth()
    pollTimer = setInterval(() => {
      void pollIndexStatus()
    }, 2000)
    queueStatusTimer = setInterval(() => {
      void loadQueueStatus()
      void loadQueueHealth()
    }, 5000)
    watch(
      () => data.value,
      () => syncPendingFromTable(),
      { deep: true, immediate: true }
    )
  })

  onBeforeUnmount(() => {
    if (pollTimer) clearInterval(pollTimer)
    if (queueStatusTimer) clearInterval(queueStatusTimer)
  })
</script>

<style scoped>
  .index-cell {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .index-msg {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    line-height: 1.2;
  }
</style>
