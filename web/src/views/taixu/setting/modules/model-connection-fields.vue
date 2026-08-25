<template>
  <ElFormItem label="BaseUrl">
    <ElInput v-model="form.baseUrl" placeholder="请输入 BaseUrl" />
  </ElFormItem>
  <ElFormItem label="ApiKey">
    <ElInput v-model="form.apiKey" placeholder="请输入ApiKey" />
  </ElFormItem>
</template>

<script setup lang="ts">
  defineProps<{ form: Record<string, string> }>()
</script>
