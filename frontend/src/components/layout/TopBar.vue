<script setup lang="ts">
import { computed } from 'vue'
import { useTheme, type ThemePreference } from '@/composables/useTheme'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const { themePreference, setThemePreference } = useTheme()

const themeOptions: { value: ThemePreference; label: string }[] = [
  { value: 'light', label: '浅色模式' },
  { value: 'dark', label: '深色模式' },
  { value: 'system', label: '跟随系统' },
]

const roleLabel = computed(() => {
  if (store.user?.role === 'admin') return '管理员'
  if (store.user?.role === 'legal') return '法务部'
  return '市场部'
})
</script>

<template>
  <header class="topbar">
    <div class="flex-1" />
    <div class="topbar-theme-switcher" aria-label="主题设置">
      <button
        v-for="option in themeOptions"
        :key="option.value"
        type="button"
        class="topbar-theme-btn"
        :class="{ active: themePreference === option.value }"
        :aria-label="option.label"
        :title="option.label"
        :aria-pressed="themePreference === option.value"
        @click="setThemePreference(option.value)"
      >
        <svg v-if="option.value === 'light'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4V2m0 20v-2m8-8h2M2 12h2m14.95 6.95 1.41 1.41M3.64 3.64l1.41 1.41m0 13.9-1.41 1.41M20.36 3.64l-1.41 1.41M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z" />
        </svg>
        <svg v-else-if="option.value === 'dark'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 14.5A8.5 8.5 0 0 1 9.5 3 7 7 0 1 0 21 14.5Z" />
        </svg>
        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5h16v10H4V5Zm4 16h8m-5-3h2" />
        </svg>
      </button>
    </div>
    <div class="topbar-user">
      <div class="topbar-avatar">
        {{ store.user?.display_name?.slice(0, 1) || '用' }}
      </div>
      <div class="hidden lg:block ml-2 min-w-0">
        <p class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{{ store.user?.display_name }}</p>
        <p class="text-xs text-gray-400">{{ roleLabel }}</p>
      </div>
    </div>
  </header>
</template>
