<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="720px"
    align-center
    destroy-on-close
  >
    <div v-loading="loading">
      <div v-if="localDir" class="dir-meta muted">目录：{{ localDir }}</div>
      <el-table v-if="files.length" :data="files" size="small" stripe max-height="420">
        <el-table-column prop="name" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column label="大小" width="100">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="mtime" label="修改时间" width="170" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-link
              v-if="row.url"
              :href="resolveStaticUrl(row.url)"
              target="_blank"
              type="primary"
              :underline="false"
            >
              打开
            </el-link>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else-if="!loading" :description="emptyText" />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
  import { ElMessage } from 'element-plus'
  import api from '@/api/video'

  const visible = defineModel<boolean>({ default: false })
  const props = defineProps<{ videoId?: number | null }>()

  const loading = ref(false)
  const localDir = ref('')
  const title = ref('')
  const files = ref<
    Array<{ name: string; size: number; mtime?: string | null; ext?: string | null; url?: string | null }>
  >([])

  const dialogTitle = computed(() => (title.value ? `已下载文件 — ${title.value}` : '已下载文件'))
  const emptyText = computed(() =>
    localDir.value ? '目录为空或尚无文件' : '该视频尚未下载到本地'
  )

  const formatSize = (n: number) => {
    const v = Number(n || 0)
    if (v < 1024) return `${v} B`
    if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`
    if (v < 1024 * 1024 * 1024) return `${(v / 1024 / 1024).toFixed(1)} MB`
    return `${(v / 1024 / 1024 / 1024).toFixed(2)} GB`
  }

  /** 开发环境 /static 在后端 8181；避免落到前端端口 */
  const resolveStaticUrl = (path?: string | null) => {
    if (!path) return ''
    if (/^https?:\/\//i.test(path)) return path
    const p = path.startsWith('/') ? path : `/${path}`
    if (import.meta.env.DEV) {
      const base = String(import.meta.env.VITE_API_PROXY_URL || 'http://localhost:8181').replace(
        /\/$/,
        ''
      )
      return `${base}${p}`
    }
    const api = String(import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
    if (/^https?:\/\//i.test(api)) {
      try {
        return `${new URL(api).origin}${p}`
      } catch {
        // ignore
      }
    }
    return p
  }

  watch(visible, async (val) => {
    if (!val || !props.videoId) {
      files.value = []
      localDir.value = ''
      title.value = ''
      return
    }
    loading.value = true
    try {
      const data = await api.localFiles(props.videoId)
      title.value = data?.title || ''
      localDir.value = data?.local_dir || ''
      files.value = data?.files || []
    } catch (e: any) {
      ElMessage.error(e?.message || '获取文件列表失败')
      files.value = []
    } finally {
      loading.value = false
    }
  })
</script>

<style scoped>
  .dir-meta {
    margin-bottom: 10px;
    font-size: 12px;
    word-break: break-all;
  }
  .muted {
    color: var(--el-text-color-secondary);
  }
</style>
