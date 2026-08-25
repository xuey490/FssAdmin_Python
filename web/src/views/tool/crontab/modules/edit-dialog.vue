<template>
  <el-dialog
    v-model="visible"
    :title="dialogType === 'add' ? '新增定时任务' : '编辑定时任务'"
    width="860px"
    align-center
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="120px">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="任务名称" prop="job_name">
            <el-input v-model="formData.job_name" placeholder="请输入任务名称" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="任务组名" prop="job_group">
            <el-input v-model="formData.job_group" placeholder="请输入任务组名" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="调用目标" prop="invoke_target">
        <el-autocomplete
          v-model="formData.invoke_target"
          :fetch-suggestions="queryTasks"
          placeholder="如 task.monitorSystem() 或 dailyBackup('param')"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="定时规则" prop="task_style">
        <el-space wrap>
          <el-select v-model="formData.task_style" :style="{ width: '100px' }">
            <el-option :value="1" label="每天" />
            <el-option :value="2" label="每小时" />
            <el-option :value="3" label="N小时" />
            <el-option :value="4" label="N分钟" />
            <el-option :value="5" label="N秒" />
            <el-option :value="6" label="每周" />
            <el-option :value="7" label="每月" />
            <el-option :value="8" label="每年" />
          </el-select>
          <template v-if="formData.task_style == 8">
            <el-input-number v-model="formData.month" :min="1" :max="12" controls-position="right" />
            <span>月</span>
          </template>
          <template v-if="formData.task_style > 6">
            <el-input-number v-model="formData.day" :min="1" :max="31" controls-position="right" />
            <span>日</span>
          </template>
          <el-select v-if="formData.task_style == 6" v-model="formData.week" :style="{ width: '100px' }">
            <el-option :value="1" label="周一" />
            <el-option :value="2" label="周二" />
            <el-option :value="3" label="周三" />
            <el-option :value="4" label="周四" />
            <el-option :value="5" label="周五" />
            <el-option :value="6" label="周六" />
            <el-option :value="0" label="周日" />
          </el-select>
          <template v-if="[1, 3, 6, 7, 8].includes(formData.task_style)">
            <el-input-number v-model="formData.hour" :min="0" :max="23" controls-position="right" />
            <span>时</span>
          </template>
          <template v-if="formData.task_style != 5">
            <el-input-number v-model="formData.minute" :min="0" :max="59" controls-position="right" />
            <span>分</span>
          </template>
          <template v-if="formData.task_style == 5">
            <el-input-number v-model="formData.second" :min="1" :max="59" controls-position="right" />
            <span>秒</span>
          </template>
        </el-space>
      </el-form-item>

      <el-form-item label="Cron表达式">
        <el-input v-model="previewCron" readonly />
      </el-form-item>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="错误策略" prop="misfire_policy">
            <el-select v-model="formData.misfire_policy" style="width: 100%">
              <el-option label="立即执行" value="1" />
              <el-option label="执行一次" value="2" />
              <el-option label="放弃执行" value="3" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="并发执行" prop="concurrent">
            <el-radio-group v-model="formData.concurrent">
              <el-radio value="0">允许</el-radio>
              <el-radio value="1">禁止</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="formData.status">
          <el-radio value="0">正常</el-radio>
          <el-radio value="1">暂停</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="备注" prop="remark">
        <el-input v-model="formData.remark" type="textarea" :rows="2" placeholder="请输入备注" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSubmit">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
  import api from '@/api/tool/crontab'
  import { ElMessage } from 'element-plus'
  import type { FormInstance, FormRules } from 'element-plus'
  import { buildCronExpression, parseCronExpression } from '../utils/cron'

  interface Props {
    modelValue: boolean
    dialogType: string
    data?: Record<string, any>
  }

  interface Emits {
    (e: 'update:modelValue', value: boolean): void
    (e: 'success'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: false,
    dialogType: 'add',
    data: undefined
  })

  const emit = defineEmits<Emits>()
  const formRef = ref<FormInstance>()
  const taskOptions = ref<string[]>([])

  const visible = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value)
  })

  const rules = reactive<FormRules>({
    job_name: [{ required: true, message: '任务名称不能为空', trigger: 'blur' }],
    job_group: [{ required: true, message: '任务组名不能为空', trigger: 'blur' }],
    invoke_target: [{ required: true, message: '调用目标不能为空', trigger: 'blur' }],
    task_style: [{ required: true, message: '定时规则不能为空', trigger: 'change' }]
  })

  const initialFormData = {
    id: null as number | null,
    job_name: '',
    job_group: 'DEFAULT',
    invoke_target: '',
    misfire_policy: '3',
    concurrent: '1',
    status: '0',
    remark: '',
    task_style: 1,
    month: 1,
    day: 1,
    week: 1,
    hour: 0,
    minute: 0,
    second: 1
  }

  const formData = reactive({ ...initialFormData })

  const previewCron = computed(() =>
    buildCronExpression({
      task_style: formData.task_style,
      second: formData.second,
      minute: formData.minute,
      hour: formData.hour,
      day: formData.day,
      month: formData.month,
      week: formData.week
    })
  )

  watch(
    () => props.modelValue,
    (newVal) => {
      if (newVal) initPage()
    }
  )

  const initPage = async () => {
    Object.assign(formData, initialFormData)
    try {
      taskOptions.value = (await api.tasks()) || []
    } catch {
      taskOptions.value = []
    }

    if (props.dialogType === 'edit' && props.data?.id) {
      const detail = await api.detail(props.data.id)
      fillForm(detail)
    }
  }

  const fillForm = (data: Record<string, any>) => {
    Object.assign(formData, {
      id: data.job_id ?? data.id,
      job_name: data.job_name,
      job_group: data.job_group || 'DEFAULT',
      invoke_target: data.invoke_target,
      misfire_policy: `${data.misfire_policy ?? '3'}`,
      concurrent: `${data.concurrent ?? '1'}`,
      status: `${data.status ?? '0'}`,
      remark: data.remark || '',
      ...parseCronExpression(data.cron_expression)
    })
  }

  const queryTasks = (queryString: string, cb: (results: Array<{ value: string }>) => void) => {
    const list = taskOptions.value
      .filter((item) => !queryString || item.includes(queryString))
      .map((item) => ({ value: `${item}()` }))
    cb(list)
  }

  const handleClose = () => {
    visible.value = false
    formRef.value?.resetFields()
  }

  const handleSubmit = async () => {
    if (!formRef.value) return
    try {
      await formRef.value.validate()
      const payload = {
        job_name: formData.job_name,
        job_group: formData.job_group,
        invoke_target: formData.invoke_target,
        cron_expression: previewCron.value,
        misfire_policy: formData.misfire_policy,
        concurrent: formData.concurrent,
        status: formData.status,
        remark: formData.remark
      }
      if (props.dialogType === 'add') {
        await api.create(payload)
        ElMessage.success('新增成功')
      } else if (formData.id !== null) {
        await api.update(formData.id, payload)
        ElMessage.success('修改成功')
      }
      emit('success')
      handleClose()
    } catch (error) {
      console.log('表单验证失败:', error)
    }
  }
</script>
