<template>
  <TaixuSseChat
    title="文档检索"
    source="retrieval"
    :endpoint="taixuRetrievalRag"
    :pattern-options="patternOptions"
    default-pattern="NativeRAG"
    :show-library="true"
    welcome-message="你好！我是 文档检索助手，请选择知识库后开始提问。"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuRetrievalRag } from '@/api/taixu'

  defineOptions({ name: 'TaixuRetrievalPage' })

  const patternOptions = [
    { value: 'NativeRAG', label: 'NativeRAG（原生RAG）' },
    { value: 'MultiQuery', label: 'MultiQuery（多问题）' },
    { value: 'RAGFusion', label: 'RAGFusion（检索融合）' },
    { value: 'SubQuestion', label: 'SubQuestion（子问题）' },
    { value: 'StepBack', label: 'StepBack（降级提问）' },
    { value: 'HYDE', label: 'HYDE（假设提问）' },
    { value: 'RoutingLogic', label: 'RoutingLogic（逻辑路由）' },
    { value: 'RoutingSemantic', label: 'RoutingSemantic（语义路由）' },
    { value: 'QueryConstruction', label: 'QueryConstruction（查询重构）' },
    { value: 'MultiRepresentation', label: 'MultiRepresentation（多重表示）' },
    { value: 'RAPTOR', label: 'RAPTOR（层级索引）' }
  ]
</script>
