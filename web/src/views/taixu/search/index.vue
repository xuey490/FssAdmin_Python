<template>
  <TaixuSseChat
    title="智能搜索"
    source="search"
    :endpoint="taixuSearchInvoke"
    :pattern-options="patternOptions"
    default-pattern="ReAct"
    :pattern-visible="false"
    :show-library="false"
    welcome-message="你好！我是 智能搜索助手，可产出结构化答案与可执行步骤。"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuSearchInvoke } from '@/api/taixu'

  defineOptions({ name: 'TaixuSearchPage' })

  const patternOptions = [
    { value: 'ReAct', label: 'ReAct（推理行动）' },
    { value: 'ReWOO', label: 'ReWOO（无观察推理）' },
    { value: 'PlanExecute', label: 'PlanExecute（规划执行）' },
    { value: 'Reflection', label: 'Reflection（反思型）' },
    { value: 'SelfDiscover', label: 'SelfDiscover（自发现）' },
    { value: 'Reflexion', label: 'Reflexion（反射型）' }
  ]
</script>
