<template>
  <el-dialog
    v-model="visible"
    title="新建视频链接"
    width="640px"
    align-center
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
      <el-form-item label="视频链接" prop="urlsText">
        <el-input
          v-model="formData.urlsText"
          type="textarea"
          :rows="10"
          placeholder="每行一个链接。合集 / B 站多 P 会在保存前自动解析并拆成单集入库"
        />
      </el-form-item>
      <el-form-item label="下载队列">
        <el-checkbox v-model="formData.enqueue">保存后加入下载队列（元数据获取成功后自动下载最佳画质）</el-checkbox>
      </el-form-item>
    </el-form>
    <template #footer>
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
  const emit = defineEmits<{ success: [] }>()

  const formRef = ref<FormInstance>()
  const submitting = ref(false)
  const formData = reactive({
    urlsText: '',
    enqueue: false
  })

  const rules: FormRules = {
    urlsText: [{ required: true, message: '请输入视频链接', trigger: 'blur' }]
  }

  watch(visible, (val) => {
    if (val) {
      formData.urlsText = ''
      formData.enqueue = false
    }
  })

  const handleClose = () => formRef.value?.resetFields()

  const handleSubmit = async () => {
    await formRef.value?.validate()
    const urls = formData.urlsText
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean)
    if (!urls.length) {
      ElMessage.warning('请输入至少一个链接')
      return
    }
    submitting.value = true
    try {
      const rows = await api.create({ urls, enqueue: formData.enqueue })
      const n = Array.isArray(rows) ? rows.length : 0
      ElMessage.success(n > 0 ? `保存成功，新增 ${n} 条` : '保存成功')
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  }
</script>
