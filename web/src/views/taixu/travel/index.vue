<template>
  <TaixuSseChat
    title="旅游助手"
    source="travel"
    :endpoint="taixuTravelInvoke"
    :pattern-options="patternOptions"
    default-pattern="ReAct"
    :pattern-visible="false"
    :show-library="false"
    welcome-message="你好！我是 旅游助手，可帮你规划行程与注意事项。"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuTravelInvoke } from '@/api/taixu'

  defineOptions({ name: 'TaixuTravelPage' })

  const patternOptions = [
    { value: 'ReAct', label: 'ReAct（推理行动）' },
    { value: 'PlanExecute', label: 'PlanExecute（规划执行）' },
    { value: 'Reflection', label: 'Reflection（反思型）' }
  ]
</script>
