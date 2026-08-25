<template>
  <ElDialog
    v-model="visible"
    :title="dialogType === 'add' ? '新增模型' : '编辑模型'"
    width="640px"
    align-center
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <ElForm ref="formRef" :model="formData" :rules="rules" label-width="120px">
      <ElFormItem label="模型名" prop="model_name">
        <ElInput v-model="formData.model_name" placeholder="请输入模型名" />
      </ElFormItem>
      <ElFormItem label="BaseUrl" prop="base_url">
        <ElInput v-model="formData.base_url" placeholder="请输入模型BaseUrl" />
      </ElFormItem>
      <ElFormItem label="ApiKey" prop="api_key">
        <ElInput v-model="formData.api_key" placeholder="请输入模型ApiKey" show-password />
      </ElFormItem>
      <ElFormItem label="类型" prop="type">
        <ElSelect v-model="formData.type" placeholder="请输入模型类型" style="width: 100%">
          <ElOption
            v-for="item in TAIXU_MODEL_TYPE_OPTIONS"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="来源" prop="source">
        <ElSelect v-model="formData.source" placeholder="请输入模型来源" style="width: 100%">
          <ElOption
            v-for="item in TAIXU_MODEL_SOURCE_OPTIONS"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </ElSelect>
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton type="primary" :loading="submitting" @click="handleSubmit">确定</ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
  import type { FormInstance, FormRules } from 'element-plus'
  import { ElMessage } from 'element-plus'
  import { createTaixuModel, updateTaixuModel } from '@/api/taixu'
  import { TAIXU_MODEL_SOURCE_OPTIONS, TAIXU_MODEL_TYPE_OPTIONS } from '../constants'

  const visible = defineModel<boolean>({ default: false })
  const props = defineProps<{ dialogType: 'add' | 'edit'; data?: Record<string, any> }>()
  const emit = defineEmits<{ success: [] }>()

  const formRef = ref<FormInstance>()
  const submitting = ref(false)

  const formData = reactive({
    id: '',
    model_name: '',
    base_url: '',
    api_key: '',
    type: '',
    source: ''
  })

  const rules: FormRules = {
    model_name: [{ required: true, message: '请输入模型名', trigger: 'blur' }],
    type: [{ required: true, message: '请选择类型', trigger: 'change' }],
    source: [{ required: true, message: '请选择来源', trigger: 'change' }]
  }

  watch(visible, (val) => {
    if (!val) return
    if (props.dialogType === 'edit' && props.data) {
      Object.assign(formData, {
        id: props.data.id,
        model_name: props.data.model_name || props.data.display_name || props.data.model_id || '',
        base_url: props.data.base_url || '',
        api_key: props.data.api_key || '',
        type: props.data.type || '',
        source: props.data.source || ''
      })
      return
    }
    Object.assign(formData, {
      id: '',
      model_name: '',
      base_url: '',
      api_key: '',
      type: '',
      source: ''
    })
  })

  const handleClose = () => formRef.value?.resetFields()

  const handleSubmit = async () => {
    await formRef.value?.validate()
    submitting.value = true
    try {
      if (props.dialogType === 'edit') {
        await updateTaixuModel({ ...formData })
      } else {
        await createTaixuModel({ ...formData })
      }
      ElMessage.success('保存成功')
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  }
</script>
