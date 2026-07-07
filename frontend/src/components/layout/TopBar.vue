<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const route = useRoute()
const menuOpen = ref(false)

const navItems = computed(() => [
  { label: '首页', description: '工作台与近期任务', to: '/', icon: 'home', show: true },
  { label: '提交物料', description: '提交广告内容并开始审查', to: '/submit', icon: 'submit', show: store.canSubmit },
  { label: '法务审核', description: '查看并处理待审物料', to: '/legal', icon: 'legal', show: store.isLegal },
  { label: '资料中心', description: '维护舆情案例和平台规则', to: '/admin/knowledge', icon: 'admin', show: store.isAdmin },
  { label: '法规数据库', description: '阅读五级法规知识库', to: '/knowledge', icon: 'knowledge', show: true },
].filter((item) => item.show))

const roleLabel = computed(() => {
  if (store.user?.role === 'admin') return '管理员'
  if (store.user?.role === 'legal') return '法务部'
  return '市场部'
})

function openMenu() {
  menuOpen.value = true
}

function closeMenu() {
  menuOpen.value = false
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && menuOpen.value) closeMenu()
}

function handleLogout() {
  closeMenu()
  store.logout()
}

watch(
  () => route.fullPath,
  () => closeMenu(),
)

watch(menuOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <header class="h-16 bg-white border-b border-gray-200 flex items-center px-3 sm:px-4 shrink-0 relative z-40">
    <button
      type="button"
      class="w-12 h-12 inline-flex items-center justify-center rounded-xl text-gray-600 hover:text-sky-700 hover:bg-sky-50 active:bg-sky-100 transition-colors"
      aria-label="打开主菜单"
      aria-controls="main-navigation-drawer"
      :aria-expanded="menuOpen"
      @click="openMenu"
    >
      <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>
    <h1 class="text-xl font-bold text-brand-primary ml-2">LexAd</h1>
    <span class="hidden sm:inline text-xs text-gray-400 ml-3">广告合规审查平台</span>
  </header>

  <Transition
    enter-active-class="transition-opacity duration-200"
    enter-from-class="opacity-0"
    leave-active-class="transition-opacity duration-200"
    leave-to-class="opacity-0"
  >
    <button
      v-if="menuOpen"
      type="button"
      class="fixed inset-0 bg-gray-900/35 backdrop-blur-1px cursor-default"
      style="z-index: 50"
      aria-label="关闭主菜单"
      @click="closeMenu"
    />
  </Transition>

  <Transition
    enter-active-class="transition-transform duration-250 ease-out"
    enter-from-class="-translate-x-full"
    leave-active-class="transition-transform duration-200 ease-in"
    leave-to-class="-translate-x-full"
  >
    <aside
      v-if="menuOpen"
      id="main-navigation-drawer"
      class="fixed inset-y-0 left-0 w-[300px] max-w-[86vw] bg-white shadow-2xl flex flex-col"
      style="z-index: 60"
      aria-label="主导航"
    >
      <div class="h-18 px-4 border-b border-gray-200 flex items-center shrink-0">
        <div class="w-11 h-11 rounded-xl bg-sky-500 text-white flex items-center justify-center font-bold text-lg shadow-sm">
          L
        </div>
        <div class="ml-3 min-w-0">
          <p class="font-bold text-lg text-gray-800 leading-tight">LexAd</p>
          <p class="text-xs text-gray-400 mt-0.5">v0.4.2</p>
        </div>
        <button
          type="button"
          class="ml-auto w-11 h-11 inline-flex items-center justify-center rounded-xl text-gray-500 hover:text-gray-700 hover:bg-gray-100"
          aria-label="关闭主菜单"
          @click="closeMenu"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 6l12 12M6 18L18 6" />
          </svg>
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto px-3 py-4" aria-label="功能导航">
        <p class="px-3 mb-2 text-xs font-semibold text-gray-400 tracking-wider">功能菜单</p>
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="min-h-14 flex items-center px-3 py-2.5 mb-2 rounded-xl text-gray-600 hover:bg-gray-100 hover:text-gray-800 transition-colors no-underline"
          active-class="!bg-sky-100 !text-sky-700"
          @click="closeMenu"
        >
          <span class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
            <svg v-if="item.icon === 'home'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 11.5 12 4l9 7.5M5.5 10v9h13v-9M9 19v-5h6v5" />
            </svg>
            <svg v-else-if="item.icon === 'submit'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v14M5 12h14" />
            </svg>
            <svg v-else-if="item.icon === 'legal'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v18M6 6h12M7 6 3.5 13h7L7 6Zm10 0-3.5 7h7L17 6ZM8 21h8" />
            </svg>
            <svg v-else-if="item.icon === 'admin'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7h16M6 7v12h12V7M9 11h6M9 15h4M8 4h8l1 3H7l1-3Z" />
            </svg>
            <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5v-16ZM20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5v-16Z" />
            </svg>
          </span>
          <span class="ml-3 min-w-0">
            <span class="block text-base font-medium leading-tight">{{ item.label }}</span>
            <span class="block text-xs text-gray-400 mt-1 truncate">{{ item.description }}</span>
          </span>
        </router-link>
      </nav>

      <div class="border-t border-gray-200 p-4 shrink-0">
        <div class="flex items-center mb-3">
          <div class="w-11 h-11 rounded-full bg-sky-100 text-sky-700 flex items-center justify-center font-semibold shrink-0">
            {{ store.user?.display_name?.slice(0, 1) || '用' }}
          </div>
          <div class="ml-3 min-w-0">
            <p class="text-sm font-medium text-gray-800 truncate">{{ store.user?.display_name }}</p>
            <p class="text-xs text-gray-400 mt-0.5">{{ roleLabel }} · {{ store.user?.dept_name }}</p>
          </div>
        </div>
        <button type="button" class="btn-ghost w-full min-h-12 text-sm" @click="handleLogout">
          退出登录
        </button>
      </div>
    </aside>
  </Transition>
</template>
