<template>
  <TaixuDialogWorkbench title="聊天空间" source="llm" pattern="chat" :endpoint="taixuLlmChat" />
</template>

<script setup lang="ts">
  import TaixuDialogWorkbench from '../modules/taixu-dialog-workbench.vue'
  import { taixuLlmChat } from '@/api/taixu'

  defineOptions({ name: 'TaixuLlmPage' })
</script>
