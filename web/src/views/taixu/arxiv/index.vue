<template>
  <TaixuSseChat
    title="Arxiv 检索"
    source="arxiv"
    :endpoint="taixuArxivRetrieve"
    :pattern-options="patternOptions"
    default-pattern="NativeRAG"
    :show-library="true"
    welcome-message="你好！我是 学术检索助手，可基于知识库进行严谨学术问答。（需要联网api_key）"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuArxivRetrieve } from '@/api/taixu'

  defineOptions({ name: 'TaixuArxivPage' })

  const patternOptions = [
    { value: 'NativeRAG', label: 'NativeRAG（原生RAG）' },
    { value: 'MultiQuery', label: 'MultiQuery（多问题）' },
    { value: 'RAGFusion', label: 'RAGFusion（检索融合）' },
    { value: 'HYDE', label: 'HYDE（假设提问）' },
    { value: 'QueryConstruction', label: 'QueryConstruction（查询重构）' }
  ]
</script>
