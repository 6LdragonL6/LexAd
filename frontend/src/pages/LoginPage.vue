<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await store.login(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100">
    <div class="card w-96">
      <h1 class="text-2xl font-bold text-center mb-6">LexAd 广告合规审查平台</h1>
      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
          <input v-model="username" class="input" placeholder="请输入用户名" required />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
          <input v-model="password" type="password" class="input" placeholder="请输入密码" required />
        </div>
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="loading" class="btn-primary w-full">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      <p class="text-xs text-gray-400 text-center mt-4">
        测试账户: market01 / test1234 (市场部) | legal01 / test1234 (法务部) | admin / admin123 (管理员)
      </p>
    </div>
  </div>
</template>
