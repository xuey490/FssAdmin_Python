<template>
  <div class="art-full-height taixu-setting-page">
    <div class="setting-layout">
      <aside class="setting-sidebar">
        <button
          v-for="tab in SETTING_TABS"
          :key="tab.key"
          type="button"
          class="sidebar-item"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <ArtSvgIcon :icon="tab.icon" />
          <span>{{ tab.label }}</span>
        </button>
      </aside>

      <main class="setting-main">
        <ElCard shadow="never" class="setting-card">
          <LlmPanel v-show="activeTab === 'llm'" :active="activeTab === 'llm'" />
          <RagPanel v-show="activeTab === 'rag'" :active="activeTab === 'rag'" />
          <AgentPanel v-show="activeTab === 'agent'" :active="activeTab === 'agent'" />
          <MemoryPanel v-show="activeTab === 'memory'" :active="activeTab === 'memory'" />
        </ElCard>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { SETTING_TABS, type SettingTabKey } from './constants'
  import LlmPanel from './modules/llm-panel.vue'
  import RagPanel from './modules/rag-panel.vue'
  import AgentPanel from './modules/agent-panel.vue'
  import MemoryPanel from './modules/memory-panel.vue'

  defineOptions({ name: 'TaixuSettingPage' })

  const activeTab = ref<SettingTabKey>('llm')
</script>

<style scoped>
  .taixu-setting-page {
    padding: 0;
  }

  .setting-layout {
    display: flex;
    gap: 16px;
    height: 100%;
    min-height: 0;
  }

  .setting-sidebar {
    flex-shrink: 0;
    width: 200px;
    padding: 12px 0;
    background: var(--el-bg-color);
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 12px;
  }

  .sidebar-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 14px 18px;
    border: none;
    background: transparent;
    color: var(--el-text-color-regular);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
  }

  .sidebar-item:hover {
    color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
  }

  .sidebar-item.active {
    position: relative;
    color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    font-weight: 600;
  }

  .sidebar-item.active::before {
    content: '';
    position: absolute;
    left: 0;
    top: 8px;
    bottom: 8px;
    width: 3px;
    border-radius: 0 3px 3px 0;
    background: var(--el-color-primary);
  }

  .setting-main {
    flex: 1;
    min-width: 0;
    min-height: 0;
  }

  .setting-card {
    height: 100%;
    border-radius: 12px;
    overflow: auto;
  }

  .setting-card :deep(.el-card__body) {
    min-height: 100%;
  }

  @media (max-width: 768px) {
    .setting-layout {
      flex-direction: column;
    }

    .setting-sidebar {
      width: 100%;
      display: flex;
      overflow-x: auto;
      padding: 8px;
    }

    .sidebar-item {
      width: auto;
      white-space: nowrap;
      border-radius: 8px;
    }

    .sidebar-item.active::before {
      display: none;
    }
  }
</style>
