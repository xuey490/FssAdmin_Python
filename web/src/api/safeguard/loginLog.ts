import request from '@/utils/http'

/**
 * 登录日志数据API
 */
export default {
  /**
   * 数据列表
   * @param params 搜索参数
   * @returns 数据列表
   */
  list(params: Record<string, any>) {
    return request.get<Api.Common.ApiPage>({
      url: '/api/core/logs/getLoginLogPageList',
      params
    })
  },

  /**
   * 删除数据
   * @param params 数据ID（数字）或包含 ids 的对象
   * @returns
   */
  delete(params: number | string | Record<string, any>) {
    let ids: Array<number | string> = []
    if (typeof params === 'number' || typeof params === 'string') {
      ids = [params]
    } else {
      ids = params.ids || []
    }
    const idStr = ids.filter((id) => id != null && id !== '').join(',')
    return request.del<any>({
      url: '/api/core/logs/deleteLoginLog',
      params: { ids: idStr }
    })
  }
}
