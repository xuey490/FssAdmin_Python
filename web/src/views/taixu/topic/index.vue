<template>
  <TaixuSseChat
    title="主题报告"
    source="topic"
    :endpoint="taixuTopicInvoke"
    :pattern-options="patternOptions"
    default-pattern="ReAct"
    :pattern-visible="false"
    :show-library="false"
    welcome-message="你好！我是 主题报告助手，可按主题生成结构化报告。"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuTopicInvoke } from '@/api/taixu'

  defineOptions({ name: 'TaixuTopicPage' })

  const patternOptions = [
    { value: 'ReAct', label: 'ReAct（推理行动）' },
    { value: 'ReWOO', label: 'ReWOO（无观察推理）' },
    { value: 'PlanExecute', label: 'PlanExecute（规划执行）' },
    { value: 'Reflection', label: 'Reflection（反思型）' },
    { value: 'SelfDiscover', label: 'SelfDiscover（自发现）' },
    { value: 'Reflexion', label: 'Reflexion（反射型）' }
  ]
</script>
