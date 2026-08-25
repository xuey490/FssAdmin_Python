import { AppRouteRecord } from '@/types/router'

export const videoRoutes: AppRouteRecord = {
  path: '/video',
  name: 'Video',
  component: '/index/index',
  meta: {
    title: '视频下载',
    icon: 'ri:video-download-line'
  },
  children: [
    {
      path: 'list',
      name: 'VideoList',
      component: '/video/index',
      meta: {
        title: '视频列表',
        keepAlive: true
      }
    }
  ]
}
