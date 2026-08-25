<template>
  <el-dialog v-model="visible" :title="title || '预览'" width="860px" align-center destroy-on-close>
    <div class="preview-body">
      <div class="preview-toolbar">
        <div class="page-link" v-if="pageUrl">
          <span class="label">原地址</span>
          <el-link :href="pageUrl" target="_blank" type="primary" :underline="false">
            {{ pageUrl }}
          </el-link>
        </div>
        <div class="quality" v-if="qualities.length">
          <span class="label">清晰度</span>
          <el-select v-model="streamUrl" size="small" style="width: 140px" :disabled="loading">
            <el-option
              v-for="q in qualities"
              :key="q.format_id || q.url"
              :label="q.label"
              :value="q.url"
            />
          </el-select>
        </div>
      </div>

      <div class="player-wrap">
        <ArtVideoPlayer
          v-if="visible && streamUrl"
          :key="playerKey"
          :player-id="'video-preview-' + playerKey"
          :video-url="streamUrl"
          :poster-url="posterUrl || ''"
          :autoplay="true"
        />
      </div>
      <el-alert
        v-if="!streamUrl && pageUrl"
        class="mt-3"
        type="warning"
        :closable="false"
        title="未能获取播放地址，请点击上方原地址在源站观看"
      />
      <p v-if="streamUrl" class="hint">
        部分站点（如 B 站）格式浏览器可能无法播放，可切换清晰度或打开原地址。
      </p>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
  import { ElMessage } from 'element-plus'
  import ArtVideoPlayer from '@/components/core/media/art-video-player/index.vue'
  import { useUserStore } from '@/store/modules/user'
  import api from '@/api/video'

  const visible = defineModel<boolean>({ default: false })
  const props = defineProps<{
    videoId?: number | null
    meta?: {
      title?: string | null
      thumbnail?: string | null
      url?: string | null
    } | null
  }>()

  const userStore = useUserStore()
  const loading = ref(false)
  const streamUrl = ref('')
  const pageUrl = ref('')
  const posterUrl = ref('')
  const title = ref('')
  const playerKey = ref(0)
  const qualities = ref<
    Array<{ label: string; height?: number | null; url: string; format_id?: string | null }>
  >([])

  /** 带 token 的代理流地址（播放器无法带 Header） */
  const buildProxyUrl = (formatId?: string | null) => {
    const token = encodeURIComponent(userStore.accessToken || '')
    const base = `/api/platform/video/stream/${props.videoId}`
    const qs = formatId
      ? `format_id=${encodeURIComponent(formatId)}&access_token=${token}`
      : `access_token=${token}`
    return `${base}?${qs}`
  }

  const applyMeta = () => {
    title.value = props.meta?.title || '预览'
    posterUrl.value = props.meta?.thumbnail || ''
    pageUrl.value = props.meta?.url || ''
  }

  watch(visible, async (val) => {
    if (!val || !props.videoId) {
      streamUrl.value = ''
      pageUrl.value = ''
      qualities.value = []
      return
    }
    applyMeta()
    playerKey.value = Date.now()
    // 立刻用 token 代理地址初始化播放器（与改直链前一致）
    streamUrl.value = buildProxyUrl()
    qualities.value = [{ label: '最高清', url: streamUrl.value, format_id: null }]
    loading.value = true
    try {
      const data = await api.preview(props.videoId)
      title.value = data?.title || title.value || '预览'
      posterUrl.value = data?.thumbnail || posterUrl.value
      pageUrl.value = data?.page_url || pageUrl.value
      const defaultUrl = buildProxyUrl()
      const list = (data?.qualities || [])
        .filter((q) => q.format_id)
        .map((q) => ({
          label: q.label,
          height: q.height,
          format_id: q.format_id,
          url: buildProxyUrl(q.format_id)
        }))
      qualities.value = [{ label: '最高清', url: defaultUrl, format_id: null }, ...list]
      // 保持当前在「最高清」代理源，避免重复切源打断播放
      if (!streamUrl.value) streamUrl.value = defaultUrl
    } catch (e: any) {
      ElMessage.error(e?.message || '预览失败')
    } finally {
      loading.value = false
    }
  })
</script>

<style scoped lang="scss">
  .preview-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 20px;
    margin-bottom: 12px;
  }
  .page-link {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    :deep(.el-link) {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 100%;
    }
  }
  .quality {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  .label {
    color: var(--el-text-color-secondary);
    font-size: 13px;
    flex-shrink: 0;
  }
  .player-wrap {
    min-height: 360px;
    background: #000;
    border-radius: 4px;
    overflow: hidden;
  }
  .hint {
    margin: 10px 0 0;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
  .mt-3 {
    margin-top: 12px;
  }
</style>
