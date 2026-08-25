import request from '@/utils/http'

const API_PATH = '/api/task/workflow/definition'

export interface WorkflowTable {
  id?: number
  uuid?: string
  name: string
  code: string
  description?: string | null
  status?: number
  nodes?: any[]
  edges?: any[]
  created_time?: string
  updated_time?: string
}

export interface WorkflowForm {
  id?: number
  name: string
  code: string
  description?: string | null
  nodes?: any[]
  edges?: any[]
  workflow_status?: number
}

export interface WorkflowPageQuery {
  page_no?: number
  page_size?: number
  name?: string
  code?: string
  status?: number
  [key: string]: unknown
}

export interface WorkflowPageResult {
  page_no?: number
  page_size?: number
  total: number
  has_next?: boolean
  items: WorkflowTable[]
}

export interface WorkflowExecuteParams {
  workflow_id: number
  variables?: Record<string, unknown>
  business_key?: string
  job_id?: number
}

export interface WorkflowExecuteResult {
  workflow_id: number
  workflow_name: string
  status: number
  start_time?: string | null
  end_time?: string | null
  variables?: Record<string, unknown> | null
  node_results?: Record<string, unknown> | null
  error?: string | null
}

const WorkflowDefinitionAPI = {
  getWorkflowList(query: WorkflowPageQuery) {
    return request.get<WorkflowPageResult>({ url: `${API_PATH}/list`, params: query })
  },

  getWorkflowDetail(id: number) {
    return request.get<WorkflowTable>({ url: `${API_PATH}/detail/${id}` })
  },

  createWorkflow(body: WorkflowForm) {
    return request.post<WorkflowTable>({ url: `${API_PATH}/create`, data: body })
  },

  updateWorkflow(id: number, body: WorkflowForm) {
    return request.put<WorkflowTable>({ url: `${API_PATH}/update/${id}`, data: body })
  },

  deleteWorkflow(ids: number[]) {
    return request.del<void>({ url: `${API_PATH}/delete`, data: ids })
  },

  publishWorkflow(id: number, _body?: Record<string, unknown>) {
    return request.post<WorkflowTable>({ url: `${API_PATH}/publish/${id}`, data: _body })
  },

  executeWorkflow(body: WorkflowExecuteParams) {
    return request.post<WorkflowExecuteResult>({ url: `${API_PATH}/execute`, data: body })
  }
}

export default WorkflowDefinitionAPI
