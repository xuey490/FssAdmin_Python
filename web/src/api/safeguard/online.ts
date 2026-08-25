import request from '@/utils/http'

/**
 * 在线用户API
 */
export default {
  /**
   * 在线用户列表
   */
  list(params: Record<string, any>) {
    return request.get<Api.Common.ApiPage>({
      url: '/api/monitor/online/list',
      params
    })
  },

  /**
   * 强制下线
   */
  forceLogout(token: string) {
    return request.del<any>({
      url: `/api/monitor/online/${token}`
    })
  }
}
