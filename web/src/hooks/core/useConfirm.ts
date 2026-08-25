import { ElMessageBox } from 'element-plus'

export function confirmDelete(message: string) {
  return ElMessageBox.confirm(message, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
}

export function confirmBatchDelete(count: number) {
  return ElMessageBox.confirm(`确认删除选中的 ${count} 项吗？`, '批量删除', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
}
