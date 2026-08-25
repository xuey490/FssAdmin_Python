<template>
  <div class="art-full-height">
    <ElCard class="art-table-card" shadow="never">
      <ArtTableHeader v-model:columns="columnChecks" :loading="loading" @refresh="refreshData">
        <template #left>
          <ElButton v-permission="'ai:provider:save'" @click="showDialog('add')" v-ripple>新增</ElButton>
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
            <SaButton v-permission="'ai:provider:update'" type="secondary" @click="showDialog('edit', row)" />
            <SaButton v-permission="'ai:provider:delete'" type="error" @click="deleteRow(row, api.provider.delete, refreshData)" />
          </div>
        </template>
      </ArtTable>
    </ElCard>
    <EditDialog v-model="dialogVisible" :dialog-type="dialogType" :data="dialogData" @success="refreshData" />
  </div>
</template>

<script setup lang="ts">
  import { useTable } from '@/hooks/core/useTable'
  import { useSaiAdmin } from '@/composables/useSaiAdmin'
  import api from '@/api/ai-admin'
  import EditDialog from './modules/edit-dialog.vue'

  const {
    columns, columnChecks, data, loading, pagination,
    handleSizeChange, handleCurrentChange, refreshData
  } = useTable({
    core: {
      apiFn: api.provider.list,
      columnsFactory: () => [
        { prop: 'id', label: 'ID', width: 80 },
        { prop: 'code', label: '标识', minWidth: 100 },
        { prop: 'name', label: '名称', minWidth: 120 },
        { prop: 'base_url', label: 'Base URL', minWidth: 200 },
        { prop: 'api_key_masked', label: 'API Key', minWidth: 140 },
        { prop: 'adapter_type', label: '适配器', width: 140 },
        { prop: 'status', label: '状态', saiType: 'dict', saiDict: 'data_status', width: 90 },
        { prop: 'sort', label: '排序', width: 80 },
        { prop: 'operation', label: '操作', width: 160, fixed: 'right', useSlot: true }
      ]
    }
  })

  const { dialogType, dialogVisible, dialogData, showDialog, deleteRow } = useSaiAdmin()
</script>
