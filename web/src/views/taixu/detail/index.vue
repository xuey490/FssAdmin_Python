<template>
  <div class="art-full-height">
    <ElCard shadow="never">
      <ElDescriptions title="系统详情" :column="1" border>
        <ElDescriptionsItem label="模块">Rag智能系统</ElDescriptionsItem>
        <ElDescriptionsItem label="SSE 协议">event / think / data</ElDescriptionsItem>
        <ElDescriptionsItem label="向量库">Qdrant（按 tenant + library 隔离）</ElDescriptionsItem>
        <ElDescriptionsItem label="图谱">Neo4j（按 labelPrefix + tenant + library 隔离）</ElDescriptionsItem>
      </ElDescriptions>
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  defineOptions({ name: 'TaixuDetailPage' })
</script>

