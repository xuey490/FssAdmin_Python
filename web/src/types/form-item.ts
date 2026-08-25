import type { Component, VNode } from 'vue'

/** 与 art-form / art-search-bar 表单项配置对齐；从 .ts 导出，避免 env.d.ts 的 *.vue 盖掉具名类型 */
export interface FormItem {
  key: string
  label: string | (() => VNode) | Component
  labelWidth?: string | number
  type?: string
  render?: (() => VNode) | Component
  hidden?: boolean
  span?: number
  options?: Record<string, any>
  props?: Record<string, any>
  slots?: Record<string, (() => any) | undefined>
  placeholder?: string
  clearable?: boolean
}

export type SearchFormItem = FormItem

export interface FormExpose {
  validate?: (...args: unknown[]) => Promise<unknown> | undefined
  reset?: () => void
  resetFields?: () => void
  clearValidate?: () => void
}
