<template>
  <el-dialog
    v-model="visible"
    :title="dialogType === 'add' ? '新增模型' : '编辑模型'"
    width="640px"
    align-center
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="120px">
      <el-form-item label="供应商" prop="provider_id">
        <el-select v-model="formData.provider_id" placeholder="选择供应商" style="width:100%">
          <el-option v-for="p in providerOptions" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="模型编码" prop="model_code">
        <el-input v-model="formData.model_code" placeholder="deepseek-chat" />
      </el-form-item>
      <el-form-item label="展示名称" prop="name">
        <el-input v-model="formData.name" />
      </el-form-item>
      <el-form-item label="上下文窗口">
        <el-input-number v-model="formData.context_window" :min="1024" :step="1024" style="width:100%" />
      </el-form-item>
      <el-form-item label="最大输出 tokens">
        <el-input-number v-model="formData.max_output_tokens" :min="256" :step="256" style="width:100%" />
      </el-form-item>
      <el-form-item label="默认温度">
        <el-input-number v-model="formData.default_temperature" :min="0" :max="2" :step="0.1" style="width:100%" />
      </el-form-item>
      <el-form-item label="默认模型">
        <el-switch v-model="formData.is_default" :active-value="1" :inactive-value="0" />
      </el-form-item>
      <el-form-item label="状态">
        <el-radio-group v-model="formData.status">
          <el-radio value="1">正常</el-radio>
          <el-radio value="0">停用</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="排序">
        <el-input-number v-model="formData.sort" :min="0" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
  import type { FormInstance, FormRules } from 'element-plus'
  import { ElMessage } from 'element-plus'
  import api from '@/api/ai-admin'

  const visible = defineModel<boolean>({ default: false })
  const props = defineProps<{ dialogType: 'add' | 'edit'; data?: Record<string, any> }>()
  const emit = defineEmits<{ success: [] }>()

  const formRef = ref<FormInstance>()
  const submitting = ref(false)
  const providerOptions = ref<Array<{ id: string; name: string }>>([])

  const formData = reactive({
    id: '',
    provider_id: '',
    model_code: '',
    name: '',
    context_window: 32000,
    max_output_tokens: 4096,
    default_temperature: 0.7,
    is_default: 0,
    status: '1',
    sort: 0,
    remark: ''
  })

  const rules: FormRules = {
    provider_id: [{ required: true, message: '请选择供应商', trigger: 'change' }],
    model_code: [{ required: true, message: '请输入模型编码', trigger: 'blur' }],
    name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
  }

  const loadProviders = async () => {
    const res = await api.provider.options()
    providerOptions.value = res.list || []
  }

  watch(visible, async (val) => {
    if (!val) return
    await loadProviders()
    if (props.dialogType === 'edit' && props.data) {
      Object.assign(formData, {
        id: props.data.id,
        provider_id: props.data.provider_id,
        model_code: props.data.model_code,
        name: props.data.name,
        context_window: props.data.context_window,
        max_output_tokens: props.data.max_output_tokens,
        default_temperature: Number(props.data.default_temperature),
        is_default: Number(props.data.is_default),
        status: props.data.status ?? '0',
        sort: props.data.sort ?? 0,
        remark: props.data.remark ?? ''
      })
    } else {
      Object.assign(formData, {
        id: '', provider_id: '', model_code: '', name: '',
        context_window: 32000, max_output_tokens: 4096, default_temperature: 0.7,
        is_default: 0, status: '1', sort: 0, remark: ''
      })
    }
  })

  const handleClose = () => formRef.value?.resetFields()

  const handleSubmit = async () => {
    await formRef.value?.validate()
    submitting.value = true
    try {
      if (props.dialogType === 'edit') {
        await api.model.update({ ...formData })
      } else {
        await api.model.save({ ...formData })
      }
      ElMessage.success('保存成功')
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  }
</script>
