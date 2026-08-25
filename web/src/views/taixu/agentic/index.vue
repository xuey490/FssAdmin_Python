<template>
  <TaixuSseChat
    title="多智能体"
    source="agentic"
    :endpoint="taixuAgenticInvoke"
    :pattern-options="patternOptions"
    default-pattern="Supervisor"
    :pattern-visible="true"
    :show-library="false"
    welcome-message="你好！我是 多智能体编排助手，可将复杂任务拆解并协同完成。"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuAgenticInvoke } from '@/api/taixu'

  defineOptions({ name: 'TaixuAgenticPage' })

  const patternOptions = [
    { value: 'Supervisor', label: 'Supervisor（监督型）' },
    { value: 'Collaboration', label: 'Collaboration（协作型）' },
    { value: 'Hierarchical', label: 'Hierarchical（层级型）' }
  ]
</script>
