<template>
  <sa-search-bar
    ref="searchBarRef"
    v-model="formData"
    label-width="92px"
    :show-expand="false"
    @reset="handleReset"
    @search="handleSearch"
  >
    <el-col v-bind="setSpan(8)">
      <el-form-item label="登录地址" prop="ipaddr">
        <el-input v-model="formData.ipaddr" placeholder="请输入登录地址" clearable />
      </el-form-item>
    </el-col>

    <el-col v-bind="setSpan(8)">
      <el-form-item label="用户账号" prop="userName">
        <el-input v-model="formData.userName" placeholder="请输入用户账号" clearable />
      </el-form-item>
    </el-col>
  </sa-search-bar>
</template>

<script setup lang="ts">
  interface Props {
    modelValue: Record<string, any>
  }

  interface Emits {
    (e: 'update:modelValue', value: Record<string, any>): void
    (e: 'search', params: Record<string, any>): void
    (e: 'reset'): void
  }

  const props = defineProps<Props>()
  const emit = defineEmits<Emits>()

  const searchBarRef = ref()

  // 表单数据双向绑定
  const formData = computed({
    get: () => props.modelValue,
    set: (val) => emit('update:modelValue', val)
  })

  // 重置
  const handleReset = () => {
    searchBarRef.value?.ref.resetFields()
    emit('reset')
  }

  // 搜索
  const handleSearch = () => {
    emit('search', formData.value)
  }

  // 栅格占据列数
  const setSpan = (span: number) => {
    return {
      span,
      xs: 24,
      sm: 12,
      md: 8,
      lg: span,
      xl: span
    }
  }
</script>
