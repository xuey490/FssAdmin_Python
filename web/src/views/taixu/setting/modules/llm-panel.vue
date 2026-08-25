<template>
  <div v-loading="loading" class="setting-panel">
    <div class="panel-title">
      <ArtSvgIcon icon="ri:chat-smile-2-line" />
      <span>文本模型</span>
    </div>
    <ElForm label-width="120px" class="panel-form">
      <ElFormItem label="模型">
        <ElSelect
          v-model="form.sourceId"
          filterable
          placeholder="选择模型"
          style="width: 100%"
          @change="onModelChange"
        >
          <ElOption v-for="m in models" :key="m.id" :label="formatModelOptionLabel(m)" :value="m.id" />
        </ElSelect>
      </ElFormItem>
      <ModelConnectionFields :form="form" />
      <ElFormItem label="温度">
        <ElInputNumber v-model="temperature" :min="0" :max="1" :step="0.1" style="width: 100%" />
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
  import { LLM_DEFAULTS } from '../constants'
  import { useSettingPanel } from './use-setting-panel'
  import ModelConnectionFields from './model-connection-fields.vue'

  const props = defineProps<{ active: boolean }>()

  const { loading, saving, models, form, onModelChange, reset, save, formatModelOptionLabel } =
    useSettingPanel('llm', 'llm', LLM_DEFAULTS, toRef(props, 'active'))

  const temperature = computed({
    get: () => Number(form.temperature || 0),
    set: (val) => {
      form.temperature = String(val ?? 0)
    }
  })
</script>

<style scoped>
  @import './panel.css';
</style>
