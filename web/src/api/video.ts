import request from '@/utils/http'

export default {
  list(params: Record<string, any>) {
    return request.get<Api.Common.ApiPage>({
      url: '/api/platform/video/list',
      params
    })
  },
  /** 仅拉元数据+下载进度，供列表原地更新（不触发整表 loading） */
  progress(ids: Array<number | string>) {
    return request.get<
      Array<{
        video_id: number
        status?: number | null
        title?: string | null
        uploader?: string | null
        source?: string | null
        best_resolution?: string | null
        thumbnail?: string | null
        duration?: number | null
        error_msg?: string | null
        active_job_id?: number | null
        active_job_status?: number | null
        job_status?: number | null
        job_progress?: number | null
        job_speed?: string | null
        job_mode?: string | null
        job_error_msg?: string | null
        job_local_dir?: string | null
        local_dir?: string | null
      }>
    >({
      url: '/api/platform/video/progress',
      params: { ids: ids.join(',') }
    })
  },
  create(params: { urls: string[]; enqueue?: boolean }) {
    return request.post<any>({
      url: '/api/platform/video/create',
      data: params
    })
  },
  update(id: number | string, params: { url: string }) {
    return request.put<any>({
      url: '/api/platform/video/update/' + id,
      data: params
    })
  },
  refresh(id: number | string) {
    return request.post<any>({
      url: '/api/platform/video/refresh/' + id
    })
  },
  delete(id: number | string) {
    return request.del<any>({
      url: '/api/platform/video/delete/' + id
    })
  },
  preview(id: number | string) {
    return request.get<{
      stream_url: string
      page_url: string
      thumbnail?: string
      title?: string
      qualities?: Array<{
        label: string
        height?: number | null
        url: string
        format_id?: string | null
      }>
    }>({
      url: '/api/platform/video/preview/' + id
    })
  },
  formats(id: number | string) {
    return request.get<Array<Record<string, any>>>({
      url: '/api/platform/video/formats/' + id
    })
  },
  localFiles(id: number | string) {
    return request.get<{
      local_dir?: string | null
      title?: string | null
      files: Array<{
        name: string
        size: number
        mtime?: string | null
        ext?: string | null
        url?: string | null
      }>
    }>({
      url: '/api/platform/video/files/' + id
    })
  },
  download(id: number | string, params: Record<string, any>) {
    return request.post<any>({
      url: '/api/platform/video/download/' + id,
      data: params
    })
  },
  queue(params?: Record<string, any>) {
    return request.get<Api.Common.ApiPage>({
      url: '/api/platform/video/download/queue',
      params
    })
  },
  pauseJob(jobId: number | string) {
    return request.post<any>({
      url: `/api/platform/video/download/job/${jobId}/pause`
    })
  },
  resumeJob(jobId: number | string) {
    return request.post<any>({
      url: `/api/platform/video/download/job/${jobId}/resume`
    })
  },
  stopJob(jobId: number | string) {
    return request.post<any>({
      url: `/api/platform/video/download/job/${jobId}/stop`
    })
  },
  pauseAll() {
    return request.post<any>({
      url: '/api/platform/video/download/queue/pause-all'
    })
  },
  resumeAll() {
    return request.post<any>({
      url: '/api/platform/video/download/queue/resume-all'
    })
  }
}
