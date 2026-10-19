<template>
  <el-dialog
    v-model="visible"
    title="分配菜单"
    width="500px"
    align-center
    :close-on-click-modal="false"
    @open="handleOpen"
    @close="handleClose"
  >
    <el-scrollbar max-height="420px">
      <el-tree
        ref="treeRef"
        :data="menuTree"
        :props="{ label: 'label', children: 'children' }"
        node-key="id"
        show-checkbox
        default-expand-all
        :check-strictly="false"
        v-loading="loading"
      />
    </el-scrollbar>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
  import { ElMessage } from 'element-plus'
  import type { ElTree } from 'element-plus'
  import userApi from '@/api/system/user'
  import menuApi from '@/api/system/menu'

  interface Props {
    modelValue: boolean
    data?: Record<string, any>
  }

  interface Emits {
    (e: 'update:modelValue', value: boolean): void
    (e: 'success'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: false,
    data: undefined
  })

  const emit = defineEmits<Emits>()

  const treeRef = ref<InstanceType<typeof ElTree>>()
  const menuTree = ref<any[]>([])
  const loading = ref(false)
  const saving = ref(false)

  const visible = computed({
    get: () => props.modelValue,
    set: (val) => emit('update:modelValue', val)
  })

  /** 有子节点的目录 id；回显时去掉，避免 setCheckedKeys 把整棵子树勾满 */
  function collectParentIds(nodes: any[], out = new Set<number>()): Set<number> {
    for (const node of nodes || []) {
      const children = node.children
      if (children?.length) {
        out.add(Number(node.id))
        collectParentIds(children, out)
      }
    }
    return out
  }

  async function handleOpen() {
    if (!props.data?.id) return
    loading.value = true
    try {
      const [treeRes, menuIdsRes] = await Promise.all([
        menuApi.accessMenu({ tree: true }),
        userApi.getUserMenus(props.data.id)
      ])
      menuTree.value = (treeRes as any) || []
      const raw = Array.isArray(menuIdsRes) ? menuIdsRes : []
      const parentIds = collectParentIds(menuTree.value)
      const menuIds = raw
        .map((id: any) => Number(id))
        .filter((id: number) => id > 0 && !parentIds.has(id))

      await nextTick()
      treeRef.value?.setCheckedKeys(menuIds, true)
    } finally {
      loading.value = false
    }
  }

  async function handleSubmit() {
    if (!props.data?.id) return
    saving.value = true
    try {
      // 只提交完全勾选的节点；半选父目录由后端补 parent_id，避免再次打开时把已取消的子菜单勾回来
      const checkedKeys = ((treeRef.value?.getCheckedKeys(false) as Array<string | number>) || [])
        .map(Number)
        .filter((id) => id > 0)
      await userApi.saveUserMenus(props.data.id, checkedKeys)
      ElMessage.success('分配菜单成功')
      emit('success')
      visible.value = false
    } catch (e: any) {
      ElMessage.error(e?.message || '保存失败')
    } finally {
      saving.value = false
    }
  }

  function handleClose() {
    menuTree.value = []
    treeRef.value?.setCheckedKeys([])
    visible.value = false
  }
</script>
