<template>
  <TaixuSseChat
    title="特殊检索"
    source="special"
    :endpoint="taixuSpecialRag"
    :pattern-options="patternOptions"
    default-pattern="Graph"
    :show-library="true"
    welcome-message="你好！我是 特殊检索助手，支持图谱、关键字与混合检索。"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuSpecialRag } from '@/api/taixu'

  defineOptions({ name: 'TaixuSpecialPage' })

  const patternOptions = [
    { value: 'Graph', label: 'Graph（知识图谱）' },
    { value: 'KeyWord', label: 'KeyWord（关键字）' },
    { value: 'Hybrid', label: 'Hybrid（混合检索）' },
    { value: 'KMean', label: 'KMean（聚类）' },
    { value: 'MMR', label: 'MMR（最大边际相关）' }
  ]
</script>
