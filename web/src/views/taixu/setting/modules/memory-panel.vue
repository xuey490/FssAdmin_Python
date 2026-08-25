<template>
  <div v-loading="loading" class="setting-panel">
    <div class="panel-title">
      <ArtSvgIcon icon="ri:database-2-line" />
      <span>Memory 模型</span>
    </div>
    <ElForm label-width="120px" class="panel-form">
      <ElFormItem label="模型">
        <ElSelect
          v-model="form.sourceId"
          filterable
          placeholder="请选择模型"
          style="width: 100%"
          @change="onModelChange"
        >
          <ElOption v-for="m in models" :key="m.id" :label="formatModelOptionLabel(m)" :value="m.id" />
        </ElSelect>
      </ElFormItem>
      <ModelConnectionFields :form="form" />
      <ElFormItem label="topK">
        <ElInput v-model="form.topK" placeholder="5" />
      </ElFormItem>
      <ElFormItem label="窗口大小">
        <ElInput v-model="form.windowSize" placeholder="10" />
      </ElFormItem>
    </ElForm>
    <div class="panel-actions">
      <ElButton type="primary" :loading="saving" @click="save">
        <ArtSvgIcon icon="ri:save-3-line" class="mr-1" />
        保存
      </ElButton>
      <ElButton @click="reset">
        <ArtSvgIcon icon="ri:refresh-line" class="mr-1" />
        重置
      </ElButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { MEMORY_DEFAULTS } from '../constants'
  import { useSettingPanel } from './use-setting-panel'
  import ModelConnectionFields from './model-connection-fields.vue'

  const props = defineProps<{ active: boolean }>()

  const { loading, saving, models, form, onModelChange, reset, save, formatModelOptionLabel } =
    useSettingPanel('memory', 'llm', MEMORY_DEFAULTS, toRef(props, 'active'))
</script>

<style scoped>
  @import './panel.css';
</style>
