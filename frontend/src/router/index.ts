import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/pages/HomePage.vue'),
    },
    {
      path: '/review',
      name: 'review',
      component: () => import('@/pages/ReviewPage.vue'),
    },
    {
      path: '/result/:requestId',
      name: 'result',
      component: () => import('@/pages/ResultPage.vue'),
      props: true,
    },
    {
      path: '/cases',
      name: 'cases',
      component: () => import('@/pages/CasesPage.vue'),
    },
    {
      path: '/templates',
      name: 'templates',
      component: () => import('@/pages/TemplatesPage.vue'),
    },
  ],
})

export default router
