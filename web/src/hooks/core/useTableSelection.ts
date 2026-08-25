import { computed, ref } from 'vue'

export function useTableSelection<T extends { id?: number }>() {
  const selectedRows = ref<T[]>([])
  const selectedIds = computed(() =>
    selectedRows.value.map((r) => r.id).filter((id): id is number => typeof id === 'number')
  )
  const batchDeleting = ref(false)

  function onTableSelectionChange(rows: T[]) {
    selectedRows.value = rows
  }

  return { selectedRows, selectedIds, batchDeleting, onTableSelectionChange }
}
