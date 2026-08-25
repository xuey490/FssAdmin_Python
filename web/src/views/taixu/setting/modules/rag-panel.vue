<template>
  <div v-loading="loading" class="setting-panel">
    <div class="panel-title">
      <ArtSvgIcon icon="ri:search-eye-line" />
      <span>文本检索</span>
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
      <ElFormItem label="向量维度">
        <ElInputNumber v-model="dimensions" :min="0" :max="9999999999" :step="1" style="width: 100%" />
      </ElFormItem>
      <ElFormItem label="TopK">
        <ElInputNumber v-model="topK" :min="0" :max="99" :step="1" style="width: 100%" />
      </ElFormItem>
      <ElRow :gutter="16">
        <ElCol :span="12">
          <ElFormItem label="Chunk Size">
            <ElInputNumber v-model="chunkSize" :min="0" :max="99999999" :step="1" style="width: 100%" />
          </ElFormItem>
        </ElCol>
        <ElCol :span="12">
          <ElFormItem label="Chunk Overlap">
            <ElInputNumber v-model="chunkOverlap" :min="0" :max="99999999" :step="1" style="width: 100%" />
          </ElFormItem>
        </ElCol>
      </ElRow>
      <ElFormItem label="距离度量">
        <ElRadioGroup v-model="form.distance">
          <ElRadio value="COSINE">余弦距离</ElRadio>
          <ElRadio value="EUCLID">欧氏距离</ElRadio>
        </ElRadioGroup>
      </ElFormItem>
      <ElRow :gutter="16">
        <ElCol :span="12">
          <ElFormItem label="混合检索">
            <ElRadioGroup v-model="form.hybrid">
              <ElRadio value="open">开启</ElRadio>
              <ElRadio value="close">关闭</ElRadio>
            </ElRadioGroup>
          </ElFormItem>
        </ElCol>
        <ElCol :span="12">
          <ElFormItem label="混合方式">
            <ElRadioGroup v-model="form.combine">
              <ElRadio value="weight">权重</ElRadio>
              <ElRadio value="rrf">RRF</ElRadio>
            </ElRadioGroup>
          </ElFormItem>
        </ElCol>
      </ElRow>
      <ElRow :gutter="16">
        <ElCol :span="12">
          <ElFormItem label="Graph检索">
            <ElRadioGroup v-model="form.graph">
              <ElRadio value="open">开启</ElRadio>
              <ElRadio value="close">关闭</ElRadio>
            </ElRadioGroup>
          </ElFormItem>
        </ElCol>
        <ElCol :span="12">
          <ElFormItem label="检索方式">
            <ElRadioGroup v-model="form.method">
              <ElRadio value="graph">知识图谱</ElRadio>
              <ElRadio value="community">社区检测</ElRadio>
            </ElRadioGroup>
          </ElFormItem>
        </ElCol>
      </ElRow>
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
  import { RAG_DEFAULTS } from '../constants'
  import { useSettingPanel } from './use-setting-panel'
  import ModelConnectionFields from './model-connection-fields.vue'

  const props = defineProps<{ active: boolean }>()

  const { loading, saving, models, form, onModelChange, reset, save, formatModelOptionLabel } =
    useSettingPanel('rag', 'embedding', RAG_DEFAULTS, toRef(props, 'active'))

  const numField = (key: 'dimensions' | 'topK' | 'chunkSize' | 'chunkOverlap') =>
    computed({
      get: () => Number(form[key] || 0),
      set: (val) => {
        form[key] = String(val ?? 0)
      }
    })

  const dimensions = numField('dimensions')
  const topK = numField('topK')
  const chunkSize = numField('chunkSize')
  const chunkOverlap = numField('chunkOverlap')
</script>

<style scoped>
  @import './panel.css';
</style>
