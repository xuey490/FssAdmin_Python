<template>
  <TaixuSseChat
    title="TaiXu 智能"
    source="custom"
    :endpoint="taixuTopicInvoke"
    :pattern-options="patternOptions"
    default-pattern="ReAct"
    :pattern-visible="false"
    :show-library="false"
    welcome-message="你好！我是智能助手，是一位主题报告撰写专家。能根据主题、关键字、情感和总结，撰写严谨详实的主题报告，有什么可以帮您？"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuTopicInvoke } from '@/api/taixu'

  defineOptions({ name: 'TaixuCustomPage' })

  const patternOptions = [
    { value: 'ReAct', label: 'ReAct（推理行动）' },
    { value: 'PlanExecute', label: 'PlanExecute（规划执行）' },
    { value: 'Reflection', label: 'Reflection（反思型）' }
  ]
</script>
