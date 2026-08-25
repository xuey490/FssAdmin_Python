import { AppRouteRecord } from '@/types/router'

export const aiRoutes: AppRouteRecord = {
  path: '/ai',
  name: 'Ai',
  component: '/index/index',
  meta: {
    title: 'AI 助手',
    icon: 'ri:robot-2-line'
  },
  children: [
    {
      path: 'chat',
      name: 'AiChat',
      component: '/ai/chat/index',
      meta: { title: 'AI 对话', keepAlive: true }
    },
    {
      path: 'provider',
      name: 'AiProvider',
      component: '/ai/provider/index',
      meta: { title: '模型供应商', keepAlive: true, permissions: ['ai:provider:list'] }
    },
    {
      path: 'model',
      name: 'AiModel',
      component: '/ai/model/index',
      meta: { title: '模型配置', keepAlive: true, permissions: ['ai:model:list'] }
    }
  ]
}
