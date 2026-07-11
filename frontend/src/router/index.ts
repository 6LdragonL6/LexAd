import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import type { User } from '@/types'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      component: () => import('@/layouts/AuthLayout.vue'),
      children: [
        { path: '', name: 'login', component: () => import('@/pages/LoginPage.vue'), meta: { guest: true } },
      ],
    },
    { path: '/', name: 'home', component: () => import('@/pages/HomePage.vue') },
    { path: '/submit', name: 'submit', component: () => import('@/pages/SubmitPage.vue'), meta: { roles: ['marketing', 'admin'] } },
    { path: '/result/:id', name: 'result', component: () => import('@/pages/ResultPage.vue'), props: true },
    { path: '/legal', name: 'legal', component: () => import('@/pages/LegalDashboard.vue'), meta: { roles: ['marketing', 'legal', 'admin'] } },
    { path: '/legal/:id', name: 'legal-detail', component: () => import('@/pages/LegalDetail.vue'), props: true, meta: { roles: ['legal', 'admin'] } },
    { path: '/knowledge', name: 'knowledge', component: () => import('@/pages/KnowledgePage.vue') },
    { path: '/admin/knowledge', name: 'admin-knowledge', component: () => import('@/pages/AdminKnowledgePage.vue'), meta: { roles: ['admin'] } },
    { path: '/brands', name: 'brands', component: () => import('@/pages/BrandArchivePage.vue'), meta: { roles: ['marketing', 'legal', 'admin'] } },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const store = useUserStore()
  if (!store.user && localStorage.getItem('access_token')) {
    await store.fetchUser()
  }
  // Check guest meta on matched route (handles nested routes)
  if (to.matched.some(record => record.meta.guest)) {
    next()
    return
  }
  if (!store.isLoggedIn) {
    next('/login')
    return
  }
  const roles = to.meta.roles as User['role'][] | undefined
  if (roles && store.user && !roles.includes(store.user.role)) {
    next('/')
    return
  }
  next()
})

export default router
