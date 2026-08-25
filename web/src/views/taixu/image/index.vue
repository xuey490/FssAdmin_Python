<template>
  <div class="art-full-height">
    <ElCard shadow="never">
      <div class="toolbar">
        <ElInput v-model="query" placeholder="输入提示词（prompt）" />
        <ElSelect v-model="size" style="width: 180px">
          <ElOption label="1024x1024" value="1024x1024" />
          <ElOption label="1536x1024" value="1536x1024" />
          <ElOption label="1024x1536" value="1024x1536" />
          <ElOption label="512x512" value="512x512" />
          <ElOption label="256x256" value="256x256" />
        </ElSelect>
        <ElSelect v-model="format" style="width: 140px">
          <ElOption label="base64" value="b64" />
          <ElOption label="url" value="url" />
        </ElSelect>
        <ElButton type="primary" :loading="loading" :disabled="!query.trim()" @click="handleGenerate">生成</ElButton>
      </div>
      <div v-if="imageSrc" class="image-box">
        <img :src="imageSrc" alt="generated" />
      </div>
      <ElEmpty v-else description="请输入提示词并生成图片" />
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { ElMessage } from 'element-plus'
  import { taixuGenerateImage } from '@/api/taixu'

  defineOptions({ name: 'TaixuImagePage' })

  const query = ref('')
  const size = ref('1024x1024')
  const format = ref<'b64' | 'url'>('b64')
  const imageSrc = ref('')
  const loading = ref(false)

  const handleGenerate = async () => {
    loading.value = true
    try {
      imageSrc.value = await taixuGenerateImage({ query: query.value, size: size.value, format: format.value })
    } catch (e: any) {
      ElMessage.error(e?.message || '生成失败')
    } finally {
      loading.value = false
    }
  }
</script>

<style scoped>
  .toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 12px;
  }

  .image-box {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 8px;
    min-height: 520px;
  }

  .image-box img {
    max-width: 100%;
    max-height: 640px;
    border-radius: 8px;
  }
</style>
