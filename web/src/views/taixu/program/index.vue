<template>
  <TaixuSseChat
    title="编程检索"
    source="program"
    :endpoint="taixuProgramRetrieve"
    :pattern-options="patternOptions"
    default-pattern="NativeRAG"
    :show-library="true"
    welcome-message="你好！我是 编程检索助手，可结合知识库给出可运行代码与步骤。"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuProgramRetrieve } from '@/api/taixu'

  defineOptions({ name: 'TaixuProgramPage' })

  const patternOptions = [
    { value: 'NativeRAG', label: 'NativeRAG（原生RAG）' },
    { value: 'MultiQuery', label: 'MultiQuery（多问题）' },
    { value: 'RAGFusion', label: 'RAGFusion（检索融合）' },
    { value: 'SubQuestion', label: 'SubQuestion（子问题）' },
    { value: 'HYDE', label: 'HYDE（假设提问）' }
  ]
</script>
