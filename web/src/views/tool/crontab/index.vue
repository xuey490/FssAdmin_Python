<template>
  <div class="art-full-height">
    <TableSearch v-model="searchForm" @search="handleSearch" @reset="resetSearchParams" />

    <ElCard class="art-table-card" shadow="never">
      <ArtTableHeader v-model:columns="columnChecks" :loading="loading" @refresh="refreshData">
        <template #left>
          <ElSpace wrap>
            <ElButton v-permission="'tool:crontab:save'" @click="showDialog('add')" v-ripple>
              <template #icon>
                <ArtSvgIcon icon="ri:add-fill" />
              </template>
              新增
            </ElButton>
          </ElSpace>
        </template>
      </ArtTableHeader>

      <ArtTable
        ref="tableRef"
        rowKey="id"
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @sort-change="handleSortChange"
        @selection-change="handleSelectionChange"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      >
        <template #status="{ row }">
          <ElTag v-if="row.status === '0'" type="success">正常</ElTag>
          <ElTag v-else type="info">暂停</ElTag>
        </template>
        <template #concurrent="{ row }">
          <span>{{ row.concurrent === '0' ? '允许' : '禁止' }}</span>
        </template>
        <template #operation="{ row }">
          <div class="flex gap-2">
            <SaButton
              v-permission="'tool:crontab:run'"
              type="primary"
              icon="ri:play-fill"
              toolTip="运行任务"
              @click="handleRun(row)"
            />
            <SaButton
              type="primary"
              icon="ri:history-line"
              toolTip="运行日志"
              @click="showTableDialog('edit', row)"
            />
            <SaButton
              v-permission="'tool:crontab:update'"
              type="secondary"
              @click="showDialog('edit', row)"
            />
            <SaButton
              v-permission="'tool:crontab:destroy'"
              type="error"
              @click="deleteRow(row, api.delete, refreshData)"
            />
          </div>
        </template>
      </ArtTable>
    </ElCard>

    <EditDialog
      v-model="dialogVisible"
      :dialog-type="dialogType"
      :data="dialogData"
      @success="refreshData"
    />

    <LogListDialog v-model="tableVisible" :data="tableData" />
  </div>
</template>

<script setup lang="ts">
  import { useTable } from '@/hooks/core/useTable'
  import { useSaiAdmin } from '@/composables/useSaiAdmin'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import api from '@/api/tool/crontab'
  import TableSearch from './modules/table-search.vue'
  import EditDialog from './modules/edit-dialog.vue'
  import LogListDialog from './modules/log-list.vue'

  const searchForm = ref({
    job_name: undefined,
    job_group: undefined,
    status: undefined
  })

  const handleSearch = (params: Record<string, any>) => {
    Object.assign(searchParams, params)
    getData()
  }

  const {
    columns,
    columnChecks,
    data,
    loading,
    getData,
    searchParams,
    pagination,
    resetSearchParams,
    handleSortChange,
    handleSizeChange,
    handleCurrentChange,
    refreshData
  } = useTable({
    core: {
      apiFn: api.list,
      columnsFactory: () => [
        { prop: 'job_id', label: '编号', width: 80, align: 'center' },
        { prop: 'job_name', label: '任务名称', minWidth: 120 },
        { prop: 'job_group', label: '任务组名', width: 120 },
        { prop: 'cron_expression', label: 'Cron表达式', minWidth: 140 },
        { prop: 'invoke_target', label: '调用目标', minWidth: 200, showOverflowTooltip: true },
        { prop: 'concurrent', label: '并发执行', width: 100, useSlot: true },
        { prop: 'status', label: '状态', width: 90, useSlot: true },
        { prop: 'update_time', label: '更新时间', width: 170, sortable: true },
        { prop: 'operation', label: '操作', width: 180, fixed: 'right', useSlot: true }
      ]
    }
  })

  const { dialogType, dialogVisible, dialogData, showDialog, deleteRow, handleSelectionChange } =
    useSaiAdmin()

  const {
    dialogVisible: tableVisible,
    dialogData: tableData,
    showDialog: showTableDialog
  } = useSaiAdmin()

  const handleRun = (row: any) => {
    ElMessageBox.confirm(`确定要立即执行任务【${row.job_name}】吗？`, '运行任务', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      api.run(row.id).then(() => {
        ElMessage.success('任务已触发执行')
      })
    })
  }
</script>
