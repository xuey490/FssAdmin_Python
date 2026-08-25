<template>
  <el-drawer
    v-model="visible"
    :title="`任务执行日志 - ${props.data?.job_name || ''}`"
    size="72%"
    destroy-on-close
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="art-full-height">
      <div class="flex justify-between items-center mb-4">
        <ElSpace wrap>
          <el-date-picker
            v-model="searchForm.create_time"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            clearable
          />
          <el-select v-model="searchForm.status" placeholder="执行状态" clearable style="width: 120px">
            <el-option label="成功" value="0" />
            <el-option label="失败" value="1" />
          </el-select>
        </ElSpace>
        <ElSpace wrap>
          <ElButton @click="handleReset" v-ripple>重置</ElButton>
          <ElButton type="primary" @click="handleSearch" v-ripple>查询</ElButton>
        </ElSpace>
      </div>

      <ElCard class="art-table-card" shadow="never">
        <ElSpace wrap class="mb-3">
          <ElButton
            v-permission="'tool:crontab:destroy'"
            :disabled="selectedRows.length === 0"
            @click="handleDelete"
            v-ripple
          >
            删除选中
          </ElButton>
          <ElButton v-permission="'tool:crontab:destroy'" @click="handleClean" v-ripple>清空日志</ElButton>
        </ElSpace>

        <ArtTable
          ref="tableRef"
          rowKey="id"
          :loading="loading"
          :data="tableData"
          :columns="columns"
          :pagination="pagination"
          @sort-change="handleSortChange"
          @selection-change="handleSelectionChange"
          @pagination:size-change="handleSizeChange"
          @pagination:current-change="handleCurrentChange"
        >
          <template #status="{ row }">
            <ElTag v-if="row.status === '0'" type="success">成功</ElTag>
            <ElTag v-else type="danger">失败</ElTag>
          </template>
        </ArtTable>
      </ElCard>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
  import { ElMessage, ElMessageBox } from 'element-plus'
  import api from '@/api/tool/crontab'
  import { useTable } from '@/hooks/core/useTable'

  interface Props {
    modelValue: boolean
    data?: Record<string, any>
  }

  interface Emits {
    (e: 'update:modelValue', value: boolean): void
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: false,
    data: undefined
  })

  const emit = defineEmits<Emits>()
  const selectedRows = ref<Record<string, any>[]>([])
  const searchForm = ref<{
    job_name: string
    status: string | undefined
    create_time: string[]
  }>({
    job_name: '',
    status: undefined,
    create_time: []
  })

  const visible = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value)
  })

  watch(
    () => props.modelValue,
    (newVal) => {
      if (newVal) initPage()
    }
  )

  const initPage = async () => {
    if (!props.data?.job_name) {
      ElMessage.error('请先选择一个任务')
      return
    }
    searchForm.value.job_name = props.data.job_name
    refreshData()
  }

  const buildQueryParams = () => {
    const params: Record<string, any> = {
      job_name: searchForm.value.job_name
    }
    if (searchForm.value.status !== undefined && searchForm.value.status !== '') {
      params.status = searchForm.value.status
    }
    if (searchForm.value.create_time?.length === 2) {
      params.create_time = [...searchForm.value.create_time]
    }
    return params
  }

  const applySearchParams = () => {
    const query = buildQueryParams()
    delete (searchParams as Record<string, any>).params
    delete (searchParams as Record<string, any>).beginTime
    delete (searchParams as Record<string, any>).endTime
    if (!query.status) {
      delete (searchParams as Record<string, any>).status
    }
    if (!query.create_time) {
      delete (searchParams as Record<string, any>).create_time
    }
    Object.assign(searchParams, query)
  }

  const refreshData = () => {
    applySearchParams()
    getData()
  }

  const handleSearch = () => {
    (searchParams as Record<string, any>).page = 1
    refreshData()
  }

  const handleReset = () => {
    ;(searchParams as Record<string, any>).page = 1
    refreshData()
  }

  const handleSelectionChange = (selection: Record<string, any>[]) => {
    selectedRows.value = selection
  }

  const handleDelete = async () => {
    if (selectedRows.value.length < 1) return
    ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 条日志吗？`, '删除日志', {
      type: 'warning'
    }).then(() => {
      api.logDelete({ ids: selectedRows.value.map((row) => row.id) }).then(() => {
        ElMessage.success('删除成功')
        refreshData()
      })
    })
  }

  const handleClean = () => {
    ElMessageBox.confirm('确定清空全部任务日志吗？', '清空日志', { type: 'warning' }).then(() => {
      api.logClean().then(() => {
        ElMessage.success('清空成功')
        refreshData()
      })
    })
  }

  const handleClose = () => {
    visible.value = false
    selectedRows.value = []
  }

  const {
    loading,
    data: tableData,
    columns,
    getData,
    pagination,
    searchParams,
    handleSortChange,
    handleSizeChange,
    handleCurrentChange
  } = useTable({
    core: {
      apiFn: api.logList,
      immediate: false,
      columnsFactory: () => [
        { type: 'selection' },
        { prop: 'create_time', label: '执行时间', width: 170, sortable: true },
        { prop: 'job_name', label: '任务名称', minWidth: 120 },
        { prop: 'invoke_target', label: '调用目标', minWidth: 180, showOverflowTooltip: true },
        { prop: 'job_message', label: '日志信息', minWidth: 180, showOverflowTooltip: true },
        { prop: 'exception_info', label: '异常信息', minWidth: 180, showOverflowTooltip: true },
        { prop: 'status', label: '执行状态', width: 100, useSlot: true }
      ]
    }
  })
</script>
