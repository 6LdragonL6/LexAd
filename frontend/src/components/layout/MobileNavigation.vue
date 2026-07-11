<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getNavItems } from '@/config/navigation'
import { APP_VERSION } from '@/constants/app'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const menuOpen = ref(false)

const navItems = computed(() => {
  if (!store.user) return []
  return getNavItems(store.user.role)
})

function openMenu() { menuOpen.value = true }
function closeMenu() { menuOpen.value = false }

function navigate(to: string) {
  closeMenu()
  router.push(to)
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && menuOpen.value) closeMenu()
}

function handleLogout() {
  closeMenu()
  store.logout()
}

watch(() => route.fullPath, () => closeMenu())
watch(menuOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})

const roleLabel = computed(() => {
  if (store.user?.role === 'admin') return '管理员'
  if (store.user?.role === 'legal') return '法务部'
  return '市场部'
})
</script>

<template>
  <!-- Mobile top bar -->
  <header class="mobile-topbar">
    <button
      type="button"
      class="mobile-menu-btn"
      aria-label="打开主菜单"
      :aria-expanded="menuOpen"
      @click="openMenu"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 6h16M4 12h16M4 18h16" stroke-linecap="round"/>
      </svg>
    </button>
    <span class="mobile-topbar-brand">LexAd</span>
    <span class="mobile-topbar-slogan">广告合规审查平台</span>
  </header>

  <!-- Backdrop -->
  <Transition
    enter-active-class="transition-opacity duration-200"
    enter-from-class="opacity-0"
    leave-active-class="transition-opacity duration-200"
    leave-to-class="opacity-0"
  >
    <div v-if="menuOpen" class="mobile-nav-backdrop" @click="closeMenu" />
  </Transition>

  <!-- Drawer -->
  <Transition
    enter-active-class="transition-transform duration-250 ease-out"
    enter-from-class="-translate-x-full"
    leave-active-class="transition-transform duration-200 ease-in"
    leave-to-class="-translate-x-full"
  >
    <aside v-if="menuOpen" class="mobile-nav-drawer" aria-label="主导航">
      <div class="mobile-nav-header">
        <div class="sidebar-logo">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L4 6V12C4 16.5 7 20.5 12 22C17 20.5 20 16.5 20 12V6L12 2Z" fill="white" fill-opacity="0.15" stroke="white" stroke-width="1.8" stroke-linejoin="round"/>
            <path d="M8.5 12L11 14.5L15.5 9.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="ml-3 min-w-0">
          <p class="font-bold text-lg text-white leading-tight">LexAd</p>
          <p class="text-xs text-white/40 mt-0.5">v{{ APP_VERSION }}</p>
        </div>
        <button type="button" class="ml-auto w-11 h-11 flex items-center justify-center rounded-xl text-white/60 hover:text-white hover:bg-white/10" aria-label="关闭菜单" @click="closeMenu">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 6l12 12M6 18L18 6" stroke-linecap="round"/>
          </svg>
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto px-3 py-4" aria-label="功能导航">
        <button
          v-for="item in navItems"
          :key="item.route"
          class="mobile-nav-item"
          :class="{ active: route.path === item.route || (item.route !== '/' && route.path.startsWith(item.route)) }"
          @click="navigate(item.route)"
        >
          {{ item.label }}
        </button>
      </nav>

      <div class="border-t border-white/10 p-4">
        <div class="flex items-center mb-3">
          <div class="w-11 h-11 rounded-full bg-sky-500/20 text-sky-300 flex items-center justify-center font-semibold">
            {{ store.user?.display_name?.slice(0, 1) || '用' }}
          </div>
          <div class="ml-3 min-w-0">
            <p class="text-sm font-medium text-white truncate">{{ store.user?.display_name }}</p>
            <p class="text-xs text-white/40 mt-0.5">{{ roleLabel }} · {{ store.user?.dept_name }}</p>
          </div>
        </div>
        <button type="button" class="btn-ghost w-full min-h-12 text-white/70 hover:text-white hover:bg-white/5" @click="handleLogout">
          退出登录
        </button>
      </div>
    </aside>
  </Transition>
</template>
