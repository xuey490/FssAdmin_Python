<template>
  <div class="art-full-height">
    <ElCard class="art-table-card" shadow="never">
      <ArtTableHeader v-model:columns="columnChecks" :loading="loading" @refresh="refreshData">
        <template #left>
          <ElButton @click="showDialog('add')" v-ripple>新增</ElButton>
        </template>
      </ArtTableHeader>
      <ArtTable
        row-key="id"
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      >
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
  import { deleteTaixuUser, fetchTaixuUsers } from '@/api/taixu'
  import EditDialog from './modules/edit-dialog.vue'

  defineOptions({ name: 'TaixuUserPage' })

  const {
    columns,
    columnChecks,
    data,
    loading,
    pagination,
    handleSizeChange,
    handleCurrentChange,
    refreshData
  } = useTable({
    core: {
      apiFn: fetchTaixuUsers,
      paginationKey: { current: 'current_page', size: 'page_size' },
      columnsFactory: () => [
        { prop: 'id', label: 'ID', minWidth: 160 },
        { prop: 'user_name', label: '用户名', width: 160 },
        { prop: 'phone_number', label: '手机号', width: 160 },
        { prop: 'email', label: '邮箱', minWidth: 180 },
        { prop: 'create_time', label: '创建时间', width: 180 },
        { prop: 'operation', label: '操作', width: 140, fixed: 'right', useSlot: true }
      ]
    }
  })

  const dialogType = ref<'add' | 'edit'>('add')
  const dialogVisible = ref(false)
  const dialogData = ref<Record<string, any>>({})

  const showDialog = (type: 'add' | 'edit', row?: Record<string, any>) => {
    dialogType.value = type
    dialogData.value = row || {}
    dialogVisible.value = true
  }

  const handleDelete = async (row: Record<string, any>) => {
    await ElMessageBox.confirm('确定删除该用户吗？', '删除', { type: 'warning' })
    await deleteTaixuUser({ ids: String(row.id) })
    ElMessage.success('删除成功')
    await refreshData()
  }
</script>

