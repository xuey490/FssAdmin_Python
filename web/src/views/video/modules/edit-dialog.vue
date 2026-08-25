<template>
  <el-dialog
    v-model="visible"
    title="编辑视频链接"
    width="640px"
    align-center
    :close-on-click-modal="false"
  >
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="90px">
      <el-form-item label="视频链接" prop="url">
        <el-input v-model="formData.url" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button :loading="refreshing" @click="handleRefresh">重新获取信息</el-button>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
  import type { FormInstance, FormRules } from 'element-plus'
  import { ElMessage } from 'element-plus'
  import api from '@/api/video'

  const visible = defineModel<boolean>({ default: false })
  const props = defineProps<{ data?: Record<string, any> }>()
  const emit = defineEmits<{ success: [] }>()

  const formRef = ref<FormInstance>()
  const submitting = ref(false)
  const refreshing = ref(false)
  const formData = reactive({ id: 0, url: '' })

  const rules: FormRules = {
    url: [{ required: true, message: '请输入链接', trigger: 'blur' }]
  }

  watch(visible, (val) => {
    if (!val || !props.data) return
    formData.id = props.data.id
    formData.url = props.data.url || ''
  })

  const handleRefresh = async () => {
    if (!formData.id) return
    refreshing.value = true
    try {
      await api.refresh(formData.id)
      ElMessage.success('已重新获取')
      emit('success')
    } finally {
      refreshing.value = false
    }
  }

  const handleSubmit = async () => {
    await formRef.value?.validate()
    submitting.value = true
    try {
      await api.update(formData.id, { url: formData.url.trim() })
      ElMessage.success('更新成功')
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  }
</script>
