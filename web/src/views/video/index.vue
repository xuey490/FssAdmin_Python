<template>
  <ArtPageReady variant="table">
    <div class="art-full-height">
      <TableSearch v-model="searchForm" @search="handleSearch" @reset="resetSearchParams" />

      <ElCard class="art-table-card" shadow="never">
        <ArtTableHeader v-model:columns="columnChecks" :loading="loading" @refresh="refreshData">
          <template #left>
            <ElButton v-permission="'module_platform:video:create'" @click="createVisible = true" v-ripple>
              新建
            </ElButton>
            <ElButton
              v-permission="'module_platform:video:download'"
              type="primary"
              :disabled="selectedRows.length === 0"
              :loading="batchDownloading"
              @click="handleDownloadSelected"
              v-ripple
            >
              下载选中
            </ElButton>
            <ElButton v-permission="'module_platform:video:download'" @click="handlePauseAll">全局暂停</ElButton>
            <ElButton v-permission="'module_platform:video:download'" @click="handleResumeAll">全局继续</ElButton>
          </template>
        </ArtTableHeader>
        <ArtTable
          row-key="id"
          :loading="loading"
          :data="data"
          :columns="columns"
          :pagination="pagination"
          @selection-change="handleSelectionChange"
          @pagination:size-change="handleSizeChange"
          @pagination:current-change="handleCurrentChange"
        >
          <template #thumbnail="{ row }">
            <el-image
              v-if="row.thumbnail"
              :src="row.thumbnail"
              :preview-src-list="[row.thumbnail]"
              referrerpolicy="no-referrer"
              fit="cover"
              class="video-thumb"
              preview-teleported
            />
            <span v-else class="muted">—</span>
          </template>
          <template #status="{ row }">
            <ElTag v-if="row.status === 1" type="success">已获取</ElTag>
            <ElTag v-else-if="row.status === -1" type="danger">失败</ElTag>
            <ElTag v-else type="info">未获取</ElTag>
          </template>
          <template #job="{ row }">
            <div
              v-if="row.job_mode === 'best' && row.job_progress !== null && row.job_progress !== undefined"
              class="job-cell"
            >
              <ElProgress
                :percentage="Math.min(100, Math.round(Number(row.job_progress || 0)))"
                :stroke-width="10"
                :status="progressStatus(row)"
              />
              <div class="job-meta">
                <span v-if="Number(row.job_status) === 3">
                  已完成{{ Math.min(100, Math.round(Number(row.job_progress || 0))) }}%
                </span>
                <template v-else>
                  <span>{{ jobStatusText(row.job_status) }}</span>
                  <span class="muted">{{ Math.round(Number(row.job_progress || 0)) }}%</span>
                  <span v-if="row.job_speed" class="muted">{{ row.job_speed }}</span>
                </template>
              </div>
              <div v-if="row.job_error_msg" class="muted err">{{ row.job_error_msg }}</div>
            </div>
            <span v-else class="muted">—</span>
          </template>
          <template #operation="{ row }">
            <div class="flex gap-2 flex-wrap">
              <SaButton
                v-permission="'module_platform:video:update'"
                type="secondary"
                @click="openEdit(row)"
              />
              <SaButton
                v-permission="'module_platform:video:query'"
                type="success"
                icon="ri:video-add-line"
                tool-tip="预览"
                @click="openPreview(row)"
              />
              <SaButton
                v-permission="'module_platform:video:delete'"
                type="error"
                @click="handleDelete(row)"
              />
              <ElDropdown
                v-permission="'module_platform:video:download'"
                trigger="click"
                @command="(cmd: string) => handleCommand(cmd, row)"
              >
                <SaButton type="info" tool-tip="更多" />
                <template #dropdown>
                  <ElDropdownMenu>
                    <ElDropdownItem command="best">下载最佳画质</ElDropdownItem>
                    <ElDropdownItem command="custom">自定义下载</ElDropdownItem>
                    <ElDropdownItem command="audio">仅下载音频</ElDropdownItem>
                    <ElDropdownItem command="subs">仅字幕和缩略图</ElDropdownItem>
                    <ElDropdownItem command="files" divided>查看已下载文件</ElDropdownItem>
                    <ElDropdownItem
                      v-if="row.active_job_id && [0, 1].includes(activeJobStatus(row))"
                      divided
                      command="pause"
                    >
                      暂停任务
                    </ElDropdownItem>
                    <ElDropdownItem
                      v-if="row.active_job_id && [2, -1, -2].includes(activeJobStatus(row))"
                      command="resume"
                    >
                      继续任务
                    </ElDropdownItem>
                    <ElDropdownItem
                      v-if="row.active_job_id && [0, 1, 2].includes(activeJobStatus(row))"
                      command="stop"
                    >
                      停止任务
                    </ElDropdownItem>
                  </ElDropdownMenu>
                </template>
              </ElDropdown>
            </div>
          </template>
        </ArtTable>
      </ElCard>

      <CreateDialog v-model="createVisible" @success="refreshData" />
      <EditDialog v-model="editVisible" :data="editData" @success="refreshData" />
      <PreviewDialog v-model="previewVisible" :video-id="previewId" :meta="previewMeta" />
      <CustomDownloadDialog v-model="customVisible" :video-id="customId" @success="refreshData" />
      <FilesDialog v-model="filesVisible" :video-id="filesId" />
    </div>
  </ArtPageReady>
</template>

<script setup lang="ts">
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { useTable } from '@/hooks/core/useTable'
  import { useSaiAdmin } from '@/composables/useSaiAdmin'
  import api from '@/api/video'
  import CreateDialog from './modules/create-dialog.vue'
  import EditDialog from './modules/edit-dialog.vue'
  import PreviewDialog from './modules/preview-dialog.vue'
  import CustomDownloadDialog from './modules/custom-download-dialog.vue'
  import FilesDialog from './modules/files-dialog.vue'
  import TableSearch from './modules/table-search.vue'

  const { handleSelectionChange, selectedRows } = useSaiAdmin()
  const batchDownloading = ref(false)
  const searchForm = ref({
    title: undefined as string | undefined,
    uploader: undefined as string | undefined
  })

  const handleSearch = (params: Record<string, any>) => {
    Object.assign(searchParams, params)
    getData()
  }

  const createVisible = ref(false)
  const editVisible = ref(false)
  const editData = ref<Record<string, any>>()
  const previewVisible = ref(false)
  const previewId = ref<number | null>(null)
  const previewMeta = ref<{ title?: string | null; thumbnail?: string | null; url?: string | null } | null>(
    null
  )
  const customVisible = ref(false)
  const customId = ref<number | null>(null)
  const filesVisible = ref(false)
  const filesId = ref<number | null>(null)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  const jobStatusText = (s: number) =>
    ({ 0: '排队', 1: '下载中', 2: '已暂停', 3: '完成', [-1]: '失败', [-2]: '已停止' } as Record<number, string>)[
      s
    ] || String(s)

  const activeJobStatus = (row: any) =>
    Number(row.active_job_status ?? row.job_status)

  /** 进度条状态：仅 status=完成 才标 success */
  const progressStatus = (row: any) => {
    if (Number(row.job_status) === -1) return 'exception'
    if (Number(row.job_status) === 2) return 'warning'
    if (Number(row.job_status) === 3) return 'success'
    return undefined
  }

  /** 有进行中的 best 任务时轮询 */
  const isBestDownloading = (row: any) =>
    row.job_mode === 'best' && [0, 1, 2].includes(Number(row.job_status))

  const {
    columns,
    columnChecks,
    data,
    loading,
    getData,
    searchParams,
    pagination,
    resetSearchParams,
    handleSizeChange,
    handleCurrentChange,
    refreshData
  } = useTable({
    core: {
      apiFn: api.list,
      apiParams: {
        page_no: 1,
        page_size: 10,
        ...searchForm.value
      },
      paginationKey: { current: 'page_no', size: 'page_size' },
      columnsFactory: () => [
        { type: 'selection', width: 48 },
        { prop: 'id', label: 'ID', width: 70 },
        { prop: 'thumbnail', label: '缩略图', width: 96, useSlot: true },
        { prop: 'title', label: '标题', minWidth: 180 },
        { prop: 'source', label: '来源', width: 100 },
        { prop: 'uploader', label: '作者', minWidth: 120 },
        { prop: 'best_resolution', label: '分辨率', width: 110 },
        {
          prop: 'duration',
          label: '时长',
          width: 90,
          formatter: (row: any) => {
            const d = Number(row.duration || 0)
            if (!d) return '—'
            const m = Math.floor(d / 60)
            const s = d % 60
            return `${m}:${String(s).padStart(2, '0')}`
          }
        },
        { prop: 'status', label: '信息', width: 90, useSlot: true },
        { prop: 'job', label: '下载进度', minWidth: 180, useSlot: true },
        { prop: 'operation', label: '操作', width: 220, fixed: 'right', useSlot: true }
      ]
    }
  })

  const needPoll = () =>
    (data.value || []).some((r: any) => Number(r.status) === 0 || isBestDownloading(r))

  let polling = false
  const pollProgressOnly = async () => {
    if (polling) return
    const rows = (data.value || []) as any[]
    const watchIds = rows
      .filter((r) => Number(r.status) === 0 || isBestDownloading(r))
      .map((r) => r.id)
    if (!watchIds.length) {
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
      return
    }
    polling = true
    try {
      const items = (await api.progress(watchIds)) || []
      const map = new Map(items.map((i) => [i.video_id, i]))
      let needFullRefresh = false
      for (const row of rows) {
        const p = map.get(row.id)
        if (!p) continue
        const prevStatus = Number(row.status)
        if (p.status !== null && p.status !== undefined) row.status = p.status
        if (p.title != null) row.title = p.title
        if (p.uploader != null) row.uploader = p.uploader
        if (p.source != null) row.source = p.source
        if (p.best_resolution != null) row.best_resolution = p.best_resolution
        if (p.thumbnail != null) row.thumbnail = p.thumbnail
        if (p.duration != null) row.duration = p.duration
        if (p.error_msg != null) row.error_msg = p.error_msg
        row.active_job_id = p.active_job_id
        row.active_job_status = p.active_job_status
        row.job_status = p.job_status
        row.job_progress = p.job_progress
        row.job_speed = p.job_speed
        row.job_mode = p.job_mode
        row.job_error_msg = p.job_error_msg
        row.job_local_dir = p.job_local_dir
        if (p.local_dir) row.local_dir = p.local_dir
        // 元数据从「未获取」变为终态，或下载任务结束 → 整表刷一次操作区
        if (prevStatus === 0 && Number(p.status) !== 0) needFullRefresh = true
        if (p.job_status !== null && p.job_status !== undefined && ![0, 1, 2].includes(Number(p.job_status))) {
          needFullRefresh = true
        }
      }
      if (needFullRefresh) refreshData()
    } catch {
      // 静默
    } finally {
      polling = false
    }
  }

  const setupPoll = () => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (needPoll()) {
      pollTimer = setInterval(pollProgressOnly, 2000)
    }
  }

  watch(
    () =>
      (data.value || [])
        .map((r: any) => `${r.id}:${r.status}:${r.job_status}`)
        .join(','),
    () => setupPoll()
  )
  onBeforeUnmount(() => {
    if (pollTimer) clearInterval(pollTimer)
  })

  const openEdit = (row: any) => {
    editData.value = row
    editVisible.value = true
  }

  const openPreview = (row: any) => {
    previewId.value = row.id
    previewMeta.value = {
      title: row.title,
      thumbnail: row.thumbnail,
      url: row.url
    }
    previewVisible.value = true
  }

  const handleDelete = async (row: any) => {
    await ElMessageBox.confirm(`确认删除「${row.title || row.url}」及其下载文件？`, '提示', {
      type: 'warning'
    })
    await api.delete(row.id)
    ElMessage.success('已删除')
    refreshData()
  }

  const handleDownloadSelected = async () => {
    const rows = selectedRows.value || []
    if (!rows.length) {
      ElMessage.warning('请先勾选视频')
      return
    }
    const ready = rows.filter((r: any) => Number(r.status) === 1)
    const skipped = rows.length - ready.length
    if (!ready.length) {
      ElMessage.warning('选中项尚未获取到视频信息，请稍后再试')
      return
    }
    batchDownloading.value = true
    let ok = 0
    let fail = 0
    try {
      for (const row of ready) {
        try {
          await api.download(row.id, { mode: 'best' })
          ok++
        } catch {
          fail++
        }
      }
      const parts = [`已加入下载队列 ${ok} 条`]
      if (skipped) parts.push(`跳过未获取信息 ${skipped} 条`)
      if (fail) parts.push(`失败 ${fail} 条`)
      ElMessage[fail ? 'warning' : 'success'](parts.join('，'))
      refreshData()
    } finally {
      batchDownloading.value = false
    }
  }

  const handleCommand = async (cmd: string, row: any) => {
    try {
      if (cmd === 'best') {
        await api.download(row.id, { mode: 'best' })
        ElMessage.success('已加入队列')
      } else if (cmd === 'custom') {
        customId.value = row.id
        customVisible.value = true
        return
      } else if (cmd === 'files') {
        filesId.value = row.id
        filesVisible.value = true
        return
      } else if (cmd === 'audio') {
        await api.download(row.id, { mode: 'audio', audio_format: 'mp3' })
        ElMessage.success('已加入队列')
      } else if (cmd === 'subs') {
        await api.download(row.id, { mode: 'subs' })
        ElMessage.success('已加入队列')
      } else if (cmd === 'pause' && row.active_job_id) {
        await api.pauseJob(row.active_job_id)
        ElMessage.success('已暂停')
      } else if (cmd === 'resume' && row.active_job_id) {
        await api.resumeJob(row.active_job_id)
        ElMessage.success('已继续')
      } else if (cmd === 'stop' && row.active_job_id) {
        await api.stopJob(row.active_job_id)
        ElMessage.success('已停止')
      }
      refreshData()
    } catch (e: any) {
      ElMessage.error(e?.message || '操作失败')
    }
  }

  const handlePauseAll = async () => {
    await api.pauseAll()
    ElMessage.success('已全局暂停')
    refreshData()
  }

  const handleResumeAll = async () => {
    await api.resumeAll()
    ElMessage.success('已全局继续')
    refreshData()
  }
</script>

<style scoped>
  .video-thumb {
    width: 72px;
    height: 40px;
    border-radius: 4px;
    display: block;
  }
  .job-cell {
    min-width: 140px;
  }
  .job-meta {
    display: flex;
    gap: 8px;
    font-size: 12px;
    margin-bottom: 4px;
  }
  .muted {
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }
  .err {
    margin-top: 2px;
    color: var(--el-color-danger);
  }
</style>
