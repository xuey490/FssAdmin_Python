import request from '@/utils/http'

/**
 * 定时任务API
 */
export default {
  list(params: Record<string, any>) {
    return request.get<Api.Common.ApiPage>({
      url: '/api/tool/crontab/list',
      params
    })
  },

  tasks() {
    return request.get<string[]>({
      url: '/api/tool/crontab/tasks'
    })
  },

  detail(id: number | string) {
    return request.get<Api.Common.ApiData>({
      url: '/api/tool/crontab/detail/' + id
    })
  },

  create(params: Record<string, any>) {
    return request.post<any>({
      url: '/api/tool/crontab/create',
      data: params
    })
  },

  update(id: number | string, params: Record<string, any>) {
    return request.put<any>({
      url: '/api/tool/crontab/update/' + id,
      data: params
    })
  },

  delete(params: number | Record<string, any>) {
    const data = typeof params === 'number' ? { ids: [params] } : params
    return request.del<any>({
      url: '/api/tool/crontab/delete',
      data
    })
  },

  run(id: number | string) {
    return request.post<any>({
      url: '/api/tool/crontab/run/' + id
    })
  },

  logList(params: Record<string, any>) {
    return request.get<Api.Common.ApiPage>({
      url: '/api/tool/crontab/log/list',
      params
    })
  },

  logDelete(idOrParams: number | string | Record<string, any>) {
    const data = typeof idOrParams === 'object' ? idOrParams : { ids: [idOrParams] }
    return request.del<any>({
      url: '/api/tool/crontab/log/delete',
      data
    })
  },

  logClean() {
    return request.del<any>({
      url: '/api/tool/crontab/log/clean'
    })
  }
}
