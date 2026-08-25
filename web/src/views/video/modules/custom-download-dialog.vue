<template>
  <el-dialog
    v-model="visible"
    title="自定义下载"
    width="720px"
    align-center
    :close-on-click-modal="false"
  >
    <el-form label-width="110px">
      <el-form-item label="视频格式">
        <el-select v-model="form.format_id" filterable clearable placeholder="选择 format_id" style="width: 100%">
          <el-option
            v-for="f in videoFormats"
            :key="'v-' + f.format_id"
            :label="formatLabel(f)"
            :value="f.format_id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="音频格式">
        <el-select v-model="form.audio_format" filterable clearable placeholder="音频 format_id 或 mp3" style="width: 100%">
          <el-option label="mp3 (后处理)" value="mp3" />
          <el-option
            v-for="f in audioFormats"
            :key="'a-' + f.format_id"
            :label="formatLabel(f)"
            :value="f.format_id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="最大高度">
        <el-select v-model="form.height" clearable placeholder="可选，如 1080" style="width: 100%">
          <el-option v-for="h in [2160, 1440, 1080, 720, 480, 360]" :key="h" :label="h + 'p'" :value="h" />
        </el-select>
      </el-form-item>
      <el-form-item label="字幕语言">
        <el-input v-model="form.sub_langs" placeholder="如 zh-Hans,en（可空）" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">开始下载</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
  import { ElMessage } from 'element-plus'
  import api from '@/api/video'

  const visible = defineModel<boolean>({ default: false })
  const props = defineProps<{ videoId?: number | null }>()
  const emit = defineEmits<{ success: [] }>()

  const submitting = ref(false)
  const formats = ref<Array<Record<string, any>>>([])
  const form = reactive({
    format_id: '' as string,
    audio_format: '' as string,
    height: undefined as number | undefined,
    sub_langs: ''
  })

  const videoFormats = computed(() =>
    formats.value.filter((f) => f.vcodec && f.vcodec !== 'none')
  )
  const audioFormats = computed(() =>
    formats.value.filter((f) => (!f.vcodec || f.vcodec === 'none') && f.acodec && f.acodec !== 'none')
  )

  const formatLabel = (f: Record<string, any>) => {
    const parts = [f.format_id, f.ext, f.resolution || f.note, f.vcodec, f.acodec].filter(Boolean)
    return parts.join(' | ')
  }

  watch(visible, async (val) => {
    if (!val || !props.videoId) return
    form.format_id = ''
    form.audio_format = ''
    form.height = undefined
    form.sub_langs = ''
    try {
      formats.value = (await api.formats(props.videoId)) || []
    } catch {
      formats.value = []
      ElMessage.warning('获取格式列表失败')
    }
  })

  const handleSubmit = async () => {
    if (!props.videoId) return
    submitting.value = true
    try {
      await api.download(props.videoId, {
        mode: 'custom',
        format_id: form.format_id || undefined,
        audio_format: form.audio_format || undefined,
        height: form.height || undefined,
        sub_langs: form.sub_langs || undefined
      })
      ElMessage.success('已加入下载队列')
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  }
</script>
