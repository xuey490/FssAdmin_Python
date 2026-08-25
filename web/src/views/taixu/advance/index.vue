<template>
  <TaixuSseChat
    title="智能检索"
    source="advance"
    :endpoint="taixuRetrievalAdvance"
    :pattern-options="patternOptions"
    default-pattern="Corrective"
    :show-library="true"
    welcome-message="你好！我是智能检索助手，支持纠错、反思与自适应检索。"
  />
</template>

<script setup lang="ts">
  import TaixuSseChat from '../modules/taixu-sse-chat.vue'
  import { taixuRetrievalAdvance } from '@/api/taixu'

  defineOptions({ name: 'TaixuAdvancePage' })

  const patternOptions = [
    { value: 'Corrective', label: 'Corrective（纠错型）' },
    { value: 'SelfCheck', label: 'SelfCheck（反思型）' },
    { value: 'Adaptive', label: 'Adaptive（自适应型）' }
  ]
</script>
