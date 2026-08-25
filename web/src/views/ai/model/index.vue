<template>
  <div class="art-full-height">
    <ElCard class="art-table-card" shadow="never">
      <ArtTableHeader v-model:columns="columnChecks" :loading="loading" @refresh="refreshData">
        <template #left>
          <ElButton v-permission="'ai:model:save'" @click="showDialog('add')" v-ripple>新增</ElButton>
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
        <template #is_default="{ row }">
          <ElTag :type="row.is_default ? 'success' : 'info'">{{ row.is_default ? '是' : '否' }}</ElTag>
        </template>
        <template #operation="{ row }">
          <div class="flex gap-2">
            <SaButton v-permission="'ai:model:update'" type="secondary" @click="showDialog('edit', row)" />
            <SaButton v-permission="'ai:model:delete'" type="error" @click="deleteRow(row, api.model.delete, refreshData)" />
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
      apiFn: api.model.list,
      columnsFactory: () => [
        { prop: 'id', label: 'ID', width: 80 },
        { prop: 'name', label: '名称', minWidth: 120 },
        { prop: 'model_code', label: '模型编码', minWidth: 140 },
        { prop: 'provider_name', label: '供应商', minWidth: 120 },
        { prop: 'context_window', label: '上下文', width: 100 },
        { prop: 'max_output_tokens', label: '最大输出', width: 100 },
        { prop: 'default_temperature', label: '温度', width: 80 },
        { prop: 'is_default', label: '默认', width: 80, useSlot: true },
        { prop: 'status', label: '状态', saiType: 'dict', saiDict: 'data_status', width: 90 },
        { prop: 'operation', label: '操作', width: 160, fixed: 'right', useSlot: true }
      ]
    }
  })

  const { dialogType, dialogVisible, dialogData, showDialog, deleteRow } = useSaiAdmin()
</script>
