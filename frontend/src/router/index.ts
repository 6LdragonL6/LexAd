// Vue Router 路由配置 —— 定义 5 条懒加载路由
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',                           // 首页
      name: 'home',
      component: () => import('@/pages/HomePage.vue'),
    },
    {
      path: '/review',                     // 广告审查提交页
      name: 'review',
      component: () => import('@/pages/ReviewPage.vue'),
    },
    {
      path: '/result/:requestId',          // 审查结果页（动态路由参数）
      name: 'result',
      component: () => import('@/pages/ResultPage.vue'),
      props: true,
    },
    {
      path: '/cases',                      // 案例库页
      name: 'cases',
      component: () => import('@/pages/CasesPage.vue'),
    },
    {
      path: '/templates',                  // 改写模板库页
      name: 'templates',
      component: () => import('@/pages/TemplatesPage.vue'),
    },
  ],
})

export default router
