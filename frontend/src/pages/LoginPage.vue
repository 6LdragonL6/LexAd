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
  <div class="login-page">
    <!-- Left: Brand panel -->
    <div class="login-brand">
      <div class="login-brand-content">
        <div class="flex items-center gap-3 mb-10">
          <div class="sidebar-logo" style="width:40px;height:40px;background:rgba(14,165,233,0.2);border-radius:8px;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L4 6V12C4 16.5 7 20.5 12 22C17 20.5 20 16.5 20 12V6L12 2Z" fill="white" fill-opacity="0.15" stroke="white" stroke-width="1.8" stroke-linejoin="round"/>
              <path d="M8.5 12L11 14.5L15.5 9.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <span class="text-white text-2xl font-bold">LexAd</span>
        </div>
        <h1 class="login-title">智能合规 · 广告无忧</h1>
        <p class="login-subtitle">让每一则广告都经得起法律检验</p>
        <div class="login-features">
          <div class="login-feature-item">
            <div class="login-feature-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M9 12l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
            <div>
              <p class="text-white text-[15px] font-semibold">AI 双轴风险审查</p>
              <p class="text-white/50 text-[13px]">法律合规 + 舆情风险双重分析</p>
            </div>
          </div>
          <div class="login-feature-item">
            <div class="login-feature-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M3 6l9-3 9 3M3 6v12l9 3 9-3V6M3 6l9 3 9-3M12 9v12" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
            <div>
              <p class="text-white text-[15px] font-semibold">法律规则引擎</p>
              <p class="text-white/50 text-[13px]">四层审核：L1~L4 法律与平台规则</p>
            </div>
          </div>
          <div class="login-feature-item">
            <div class="login-feature-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
            <div>
              <p class="text-white text-[15px] font-semibold">舆情风险预警</p>
              <p class="text-white/50 text-[13px]">历史舆情案例匹配与品牌风险提示</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right: Login form -->
    <div class="login-form-panel">
      <h2 class="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-2">欢迎登录</h2>
      <p class="text-sm text-gray-400 mb-8">请输入您的账号信息以继续</p>
      <form @submit.prevent="handleLogin" class="space-y-5">
        <div>
          <label class="label">用户名</label>
          <input v-model="username" class="input" placeholder="请输入用户名" required />
        </div>
        <div>
          <label class="label">密码</label>
          <input v-model="password" type="password" class="input" placeholder="请输入密码" required />
        </div>
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="loading" class="btn-primary w-full min-h-12 text-[15px]">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      <div class="mt-7 p-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
        <p class="text-xs text-gray-400 font-semibold mb-2">测试账号</p>
        <p class="text-xs text-gray-600 dark:text-gray-300">market01 / test1234（市场部）</p>
        <p class="text-xs text-gray-600 dark:text-gray-300">legal01 / test1234（法务部）</p>
        <p class="text-xs text-gray-600 dark:text-gray-300">admin / admin123（管理员）</p>
      </div>
    </div>
  </div>
</template>
