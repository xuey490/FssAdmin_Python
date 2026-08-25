<template>
  <el-dialog
    v-model="visible"
    :title="dialogType === 'add' ? '新增供应商' : '编辑供应商'"
    width="640px"
    align-center
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="110px">
      <el-form-item label="标识 code" prop="code">
        <el-input v-model="formData.code" :disabled="dialogType === 'edit'" placeholder="如 deepseek" />
      </el-form-item>
      <el-form-item label="名称" prop="name">
        <el-input v-model="formData.name" placeholder="展示名称" />
      </el-form-item>
      <el-form-item label="Base URL" prop="base_url">
        <el-input v-model="formData.base_url" placeholder="https://api.deepseek.com/v1" />
      </el-form-item>
      <el-form-item label="API Key" prop="api_key">
        <el-input
          v-model="formData.api_key"
          type="password"
          show-password
          :placeholder="dialogType === 'edit' ? '留空则不修改' : '必填'"
        />
      </el-form-item>
      <el-form-item label="适配器">
        <el-input v-model="formData.adapter_type" placeholder="openai_compatible" />
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
      <el-form-item label="备注">
        <el-input v-model="formData.remark" type="textarea" :rows="2" />
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
  const formData = reactive({
    id: '',
    code: '',
    name: '',
    base_url: 'https://api.deepseek.com/v1',
    api_key: '',
    adapter_type: 'openai_compatible',
    status: '1',
    sort: 0,
    remark: ''
  })

  const rules: FormRules = {
    code: [{ required: true, message: '请输入 code', trigger: 'blur' }],
    name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
    base_url: [{ required: true, message: '请输入 Base URL', trigger: 'blur' }],
    api_key: [{
      validator: (_r, v, cb) => {
        if (props.dialogType === 'add' && !v) cb(new Error('请输入 API Key'))
        else cb()
      },
      trigger: 'blur'
    }]
  }

  watch(visible, (val) => {
    if (!val) return
    if (props.dialogType === 'edit' && props.data) {
      Object.assign(formData, {
        id: props.data.id,
        code: props.data.code,
        name: props.data.name,
        base_url: props.data.base_url,
        api_key: '',
        adapter_type: props.data.adapter_type || 'openai_compatible',
        status: props.data.status ?? '0',
        sort: props.data.sort ?? 0,
        remark: props.data.remark ?? ''
      })
    } else {
      Object.assign(formData, {
        id: '', code: '', name: '', base_url: 'https://api.deepseek.com/v1',
        api_key: '', adapter_type: 'openai_compatible', status: '1', sort: 0, remark: ''
      })
    }
  })

  const handleClose = () => formRef.value?.resetFields()

  const handleSubmit = async () => {
    await formRef.value?.validate()
    submitting.value = true
    try {
      const payload = { ...formData }
      if (props.dialogType === 'edit') {
        if (!payload.api_key) delete (payload as any).api_key
        await api.provider.update(payload)
      } else {
        await api.provider.save(payload)
      }
      ElMessage.success('保存成功')
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  }
</script>
