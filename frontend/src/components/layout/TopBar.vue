<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const menuOpen = ref(false)

const navItems = [
  { label: '首页', to: '/' },
  { label: '提交物料', to: '/submit' },
  { label: '法务审核', to: '/legal', show: () => store.isLegal },
  { label: '法规数据库', to: '/knowledge' },
]

function closeMenu() {
  menuOpen.value = false
}
</script>

<template>
  <header class="h-14 bg-white border-b border-gray-200 flex items-center px-4 lg:px-6 shrink-0 relative">
    <h1 class="text-lg font-bold text-brand-primary mr-4 lg:mr-8 shrink-0">LexAd</h1>

    <!-- Desktop nav -->
    <nav class="hidden lg:flex gap-1">
      <template v-for="item in navItems" :key="item.to">
        <router-link
          v-if="!item.show || item.show()"
          :to="item.to"
          class="px-3 py-1.5 rounded-md text-sm text-gray-600 hover:bg-gray-100"
          active-class="bg-sky-50 text-sky-700"
        >{{ item.label }}</router-link>
      </template>
    </nav>

    <!-- Mobile hamburger -->
    <button
      class="lg:hidden ml-auto mr-2 p-1.5 rounded-md text-gray-600 hover:bg-gray-100"
      @click="menuOpen = !menuOpen"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path v-if="!menuOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 6l12 12M6 18L18 6" />
      </svg>
    </button>

    <!-- Desktop user area -->
    <div class="hidden lg:flex ml-auto items-center gap-3">
      <span class="text-sm text-gray-500">{{ store.user?.display_name }}</span>
      <button @click="store.logout" class="text-sm text-gray-400 hover:text-red-500">退出</button>
    </div>

    <!-- Mobile user area (compact) -->
    <span class="lg:hidden text-sm text-gray-500 truncate max-w-100px">{{ store.user?.display_name }}</span>
    <button @click="store.logout" class="lg:hidden text-sm text-gray-400 hover:text-red-500 ml-2 shrink-0">退出</button>

    <!-- Mobile nav dropdown -->
    <nav v-if="menuOpen" class="absolute top-14 left-0 right-0 bg-white border-b border-gray-200 shadow-lg z-50 lg:hidden">
      <template v-for="item in navItems" :key="item.to">
        <router-link
          v-if="!item.show || item.show()"
          :to="item.to"
          class="block px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 border-b border-gray-100 last:border-0"
          active-class="bg-sky-50 text-sky-700"
          @click="closeMenu"
        >{{ item.label }}</router-link>
      </template>
    </nav>
  </header>
</template>
