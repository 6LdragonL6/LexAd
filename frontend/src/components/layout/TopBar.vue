<script setup lang="ts">
import { useUserStore } from '@/stores/user'

const store = useUserStore()

const navItems = [
  { label: '首页', to: '/' },
  { label: '提交物料', to: '/submit' },
  { label: '法务审核', to: '/legal', show: () => store.isLegal },
  { label: '法规数据库', to: '/knowledge' },
]
</script>

<template>
  <header class="h-14 bg-white border-b border-gray-200 flex items-center px-6 shrink-0">
    <h1 class="text-lg font-bold text-brand-primary mr-8">LexAd</h1>
    <nav class="flex gap-1">
      <template v-for="item in navItems" :key="item.to">
        <router-link
          v-if="!item.show || item.show()"
          :to="item.to"
          class="px-3 py-1.5 rounded-md text-sm text-gray-600 hover:bg-gray-100"
          active-class="bg-sky-50 text-sky-700"
        >{{ item.label }}</router-link>
      </template>
    </nav>
    <div class="ml-auto flex items-center gap-3">
      <span class="text-sm text-gray-500">{{ store.user?.display_name }}</span>
      <button @click="store.logout" class="text-sm text-gray-400 hover:text-red-500">退出</button>
    </div>
  </header>
</template>
