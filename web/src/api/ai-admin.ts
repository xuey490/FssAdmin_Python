import request from '@/utils/http'

const providerApi = {
  list(params: Record<string, any>) {
    return request.get<Api.Common.ApiPage>({ url: '/api/ai/admin/providers/list', params })
  },
  save(params: Record<string, any>) {
    return request.post<any>({ url: '/api/ai/admin/providers/create', data: params })
  },
  update(params: Record<string, any>) {
    return request.put<any>({ url: '/api/ai/admin/providers/update/' + params.id, data: params })
  },
  delete(id: string | number) {
    return request.del<any>({ url: '/api/ai/admin/providers/delete/' + id })
  },
  options() {
    return request.get<{ list: Array<{ id: string; name: string; code: string }> }>({
      url: '/api/ai/admin/providers/options'
    })
  }
}

const modelApi = {
  list(params: Record<string, any>) {
    return request.get<Api.Common.ApiPage>({ url: '/api/ai/admin/models/list', params })
  },
  save(params: Record<string, any>) {
    return request.post<any>({ url: '/api/ai/admin/models/create', data: params })
  },
  update(params: Record<string, any>) {
    return request.put<any>({ url: '/api/ai/admin/models/update/' + params.id, data: params })
  },
  delete(id: string | number) {
    return request.del<any>({ url: '/api/ai/admin/models/delete/' + id })
  }
}

export default { provider: providerApi, model: modelApi }
