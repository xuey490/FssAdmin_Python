<template>
  <TaixuSseChat
    title="智能问答"
    source="answer"
    :endpoint="taixuAgentInvoke"
    :pattern-options="patternOptions"
    default-pattern="ReAct"
    :pattern-visible="true"
    :show-library="false"
    welcome-message="你好！我是 智能问答助手，有什么可以帮您？"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuAgentInvoke } from '@/api/taixu'

  defineOptions({ name: 'TaixuAnswerPage' })

  const patternOptions = [
    { value: 'ReAct', label: 'ReAct（推理行动）' },
    { value: 'ReWOO', label: 'ReWOO（无观察推理）' },
    { value: 'PlanExecute', label: 'PlanExecute（规划执行）' },
    { value: 'Reflection', label: 'Reflection（反思型）' },
    { value: 'SelfDiscover', label: 'SelfDiscover（自发现）' },
    { value: 'Reflexion', label: 'Reflexion（反射型）' }
  ]
</script>
