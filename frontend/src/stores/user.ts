import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User } from '@/types'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isMarketing = computed(() => user.value?.role === 'marketing')
  const isLegal = computed(() => user.value?.role === 'legal' || user.value?.role === 'admin')
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username: string, password: string) {
    const res = await authApi.login(username, password)
    localStorage.setItem('access_token', res.data.access_token)
    await fetchUser()
  }

  async function fetchUser() {
    loading.value = true
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      user.value = null
      localStorage.removeItem('access_token')
    } finally {
      loading.value = false
    }
  }

  function logout() {
    user.value = null
    localStorage.removeItem('access_token')
    window.location.href = '/login'
  }

  return { user, loading, isLoggedIn, isMarketing, isLegal, isAdmin, login, fetchUser, logout }
})
