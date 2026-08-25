<template>
  <div class="art-full-height">
    <TableSearch v-model="searchForm" @search="handleSearch" @reset="resetSearchParams" />

    <ElCard class="art-table-card" shadow="never">
      <ArtTableHeader v-model:columns="columnChecks" :loading="loading" @refresh="refreshData">
        <template #left>
          <ElSpace wrap>
            <ElButton @click="showDialog('add')" v-ripple>
              <template #icon>
                <ArtSvgIcon icon="ri:add-fill" />
              </template>
              新增
            </ElButton>
            <ElButton type="danger" plain :disabled="!selectedRows.length" @click="handleBatchDelete" v-ripple>
              删除
            </ElButton>
          </ElSpace>
        </template>
      </ArtTableHeader>
      <ArtTable
        row-key="id"
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @selection-change="handleSelectionChange"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      >
        <template #type="{ row }">
          {{ getTaixuModelTypeLabel(row.type) }}
        </template>
        <template #source="{ row }">
          {{ getTaixuModelSourceLabel(row.source) }}
        </template>
        <template #api_key="{ row }">
          <span class="truncate inline-block max-w-[180px]" :title="row.api_key">{{ row.api_key || '-' }}</span>
        </template>
        <template #operation="{ row }">
          <div class="flex gap-2">
            <SaButton type="secondary" @click="showDialog('edit', row)" />
            <SaButton type="error" @click="handleDelete(row)" />
          </div>
        </template>
      </ArtTable>
    </ElCard>
    <EditDialog v-model="dialogVisible" :dialog-type="dialogType" :data="dialogData" @success="refreshData" />
  </div>
</template>

<script setup lang="ts">
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { useTable } from '@/hooks/core/useTable'
  import { deleteTaixuModel, fetchTaixuModels } from '@/api/taixu'
  import { getTaixuModelSourceLabel, getTaixuModelTypeLabel } from './constants'
  import EditDialog from './modules/edit-dialog.vue'
  import TableSearch from './modules/table-search.vue'

  defineOptions({ name: 'TaixuModelPage' })

  const searchForm = ref({
    model_name: undefined,
    type: undefined,
    source: undefined
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
    handleSizeChange,
    handleCurrentChange,
    refreshData
  } = useTable({
    core: {
      apiFn: fetchTaixuModels,
      paginationKey: { current: 'current_page', size: 'page_size' },
      columnsFactory: () => [
        { type: 'selection', width: 48 },
        { type: 'index', label: '序号', width: 70 },
        { prop: 'model_name', label: '模型名', minWidth: 180 },
        { prop: 'base_url', label: 'BaseUrl', minWidth: 220 },
        { prop: 'api_key', label: 'ApiKey', minWidth: 180, useSlot: true },
        { prop: 'type', label: '类型', width: 120, useSlot: true },
        { prop: 'source', label: '来源', width: 120, useSlot: true },
        { prop: 'create_time', label: '创建时间', width: 180 },
        { prop: 'operation', label: '操作', width: 140, fixed: 'right', useSlot: true }
      ]
    }
  })

  const dialogType = ref<'add' | 'edit'>('add')
  const dialogVisible = ref(false)
  const dialogData = ref<Record<string, any>>({})
  const selectedRows = ref<Record<string, any>[]>([])

  const showDialog = (type: 'add' | 'edit', row?: Record<string, any>) => {
    dialogType.value = type
    dialogData.value = row || {}
    dialogVisible.value = true
  }

  const handleSelectionChange = (selection: Record<string, any>[]) => {
    selectedRows.value = selection
  }

  const handleDelete = async (row: Record<string, any>) => {
    await ElMessageBox.confirm('确定删除该模型吗？', '删除', { type: 'warning' })
    await deleteTaixuModel({ ids: String(row.id) })
    ElMessage.success('删除成功')
    await refreshData()
  }

  const handleBatchDelete = async () => {
    if (!selectedRows.value.length) {
      ElMessage.warning('请选择要删除的模型')
      return
    }
    await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 个模型吗？`, '删除', {
      type: 'warning'
    })
    await deleteTaixuModel({ ids: selectedRows.value.map((row) => row.id).join(',') })
    ElMessage.success('删除成功')
    selectedRows.value = []
    await refreshData()
  }
</script>
