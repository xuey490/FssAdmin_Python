<template>
  <ElDialog
    v-model="visible"
    :title="dialogType === 'add' ? '新增用户' : '编辑用户'"
    width="640px"
    align-center
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <ElForm ref="formRef" :model="formData" :rules="rules" label-width="120px">
      <ElFormItem label="用户名" prop="user_name">
        <ElInput v-model="formData.user_name" />
      </ElFormItem>
      <ElFormItem v-if="dialogType === 'add'" label="密码" prop="password">
        <ElInput v-model="formData.password" type="password" show-password />
      </ElFormItem>
      <ElFormItem label="手机号">
        <ElInput v-model="formData.phone_number" />
      </ElFormItem>
      <ElFormItem label="邮箱">
        <ElInput v-model="formData.email" />
      </ElFormItem>
      <ElFormItem label="简介">
        <ElInput v-model="formData.resume" type="textarea" :rows="4" />
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
  import { createTaixuUser, updateTaixuUser } from '@/api/taixu'

  const visible = defineModel<boolean>({ default: false })
  const props = defineProps<{ dialogType: 'add' | 'edit'; data?: Record<string, any> }>()
  const emit = defineEmits<{ success: [] }>()

  const formRef = ref<FormInstance>()
  const submitting = ref(false)

  const formData = reactive({
    id: '',
    user_name: '',
    password: '',
    phone_number: '',
    email: '',
    resume: '',
    photo: ''
  })

  const rules: FormRules = {
    user_name: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
    password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
  }

  watch(visible, (val) => {
    if (!val) return
    if (props.dialogType === 'edit' && props.data) {
      Object.assign(formData, {
        id: props.data.id,
        user_name: props.data.user_name ?? props.data.userName ?? '',
        password: '',
        phone_number: props.data.phone_number ?? props.data.phoneNumber ?? '',
        email: props.data.email ?? '',
        resume: props.data.resume ?? '',
        photo: props.data.photo ?? ''
      })
      return
    }
    Object.assign(formData, {
      id: '',
      user_name: '',
      password: '',
      phone_number: '',
      email: '',
      resume: '',
      photo: ''
    })
  })

  const handleClose = () => formRef.value?.resetFields()

  const handleSubmit = async () => {
    await formRef.value?.validate()
    submitting.value = true
    try {
      if (props.dialogType === 'edit') {
        await updateTaixuUser({ ...formData, password: undefined })
      } else {
        await createTaixuUser({ ...formData })
      }
      ElMessage.success('保存成功')
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  }
</script>

