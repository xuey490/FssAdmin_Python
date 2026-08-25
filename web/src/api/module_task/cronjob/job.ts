import request from '@/utils/http'

const API_PATH = '/api/task/cronjob/job'

export interface SchedulerStatus {
  status: string
  is_running: boolean
  job_count: number
}

export interface SchedulerJob {
  id: string
  name: string
  trigger: string
  next_run_time?: string
  status: number
}

export interface JobLogPageQuery {
  page_no?: number
  page_size?: number
  job_id?: string
  job_name?: string
  trigger_type?: string
  status?: number
  [key: string]: unknown
}

export interface JobLogTable {
  id?: number
  job_id: string
  job_name?: string
  trigger_type?: string
  next_run_time?: string
  job_state?: string
  result?: string
  error?: string
  status?: number
  description?: string
  created_time?: string
  updated_time?: string
  tenant_id?: number
}

/** 与后端 PageResultSchema 对齐 */
export interface JobLogPageResult {
  page_no?: number
  page_size?: number
  total: number
  has_next?: boolean
  items: JobLogTable[]
}

const JobAPI = {
  getSchedulerStatus() {
    return request.get<SchedulerStatus>({ url: `${API_PATH}/scheduler/status` })
  },

  getSchedulerJobs() {
    return request.get<SchedulerJob[]>({ url: `${API_PATH}/scheduler/jobs` })
  },

  startScheduler() {
    return request.post<void>({ url: `${API_PATH}/scheduler/start` })
  },

  pauseScheduler() {
    return request.post<void>({ url: `${API_PATH}/scheduler/pause` })
  },

  resumeScheduler() {
    return request.post<void>({ url: `${API_PATH}/scheduler/resume` })
  },

  shutdownScheduler() {
    return request.post<void>({ url: `${API_PATH}/scheduler/shutdown` })
  },

  clearAllJobs() {
    return request.del<void>({ url: `${API_PATH}/scheduler/jobs/clear` })
  },

  getSchedulerConsole() {
    return request.get<string>({ url: `${API_PATH}/scheduler/console` })
  },

  syncJobsToDb() {
    return request.post<number>({ url: `${API_PATH}/scheduler/sync` })
  },

  pauseJob(jobId: string) {
    return request.post<void>({ url: `${API_PATH}/task/pause/${jobId}` })
  },

  resumeJob(jobId: string) {
    return request.post<void>({ url: `${API_PATH}/task/resume/${jobId}` })
  },

  runJobNow(jobId: string) {
    return request.post<void>({ url: `${API_PATH}/task/run/${jobId}` })
  },

  removeJob(jobId: string) {
    return request.del<void>({ url: `${API_PATH}/task/remove/${jobId}` })
  },

  getJobLogList(query: JobLogPageQuery) {
    return request.get<JobLogPageResult>({ url: `${API_PATH}/log/list`, params: query })
  },

  getJobLogDetail(id: number) {
    return request.get<JobLogTable>({ url: `${API_PATH}/log/detail/${id}` })
  },

  deleteJobLog(ids: number[]) {
    return request.del<void>({ url: `${API_PATH}/log/delete`, data: ids })
  }
}

export default JobAPI
