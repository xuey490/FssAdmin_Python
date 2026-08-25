<template>
  <div v-loading="loading" class="setting-panel">
    <div class="panel-title">
      <ArtSvgIcon icon="ri:robot-2-line" />
      <span>Agent 模型</span>
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
      <ElFormItem label="Temperature">
        <ElInput v-model="form.temperature" placeholder="0.3" />
      </ElFormItem>
      <ElFormItem label="最大迭代">
        <ElInput v-model="form.maxIterations" placeholder="10" />
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
  import { AGENT_DEFAULTS } from '../constants'
  import { useSettingPanel } from './use-setting-panel'
  import ModelConnectionFields from './model-connection-fields.vue'

  const props = defineProps<{ active: boolean }>()

  const { loading, saving, models, form, onModelChange, reset, save, formatModelOptionLabel } =
    useSettingPanel('agent', 'llm', AGENT_DEFAULTS, toRef(props, 'active'))
</script>

<style scoped>
  @import './panel.css';
</style>
