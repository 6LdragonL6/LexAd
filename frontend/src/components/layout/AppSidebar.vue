<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getNavItems } from '@/config/navigation'
import { APP_VERSION } from '@/constants/app'

const route = useRoute()
const store = useUserStore()

const navItems = computed(() => {
  if (!store.user) return []
  return getNavItems(store.user.role)
})

function isActive(itemRoute: string): boolean {
  if (itemRoute === '/') return route.path === '/'
  return route.path.startsWith(itemRoute)
}

const mainItems = computed(() => navItems.value.filter(i => i.group !== 'knowledge'))
const knowledgeItems = computed(() => navItems.value.filter(i => i.group === 'knowledge'))
</script>

<template>
  <aside class="sidebar-fixed sidebar">
    <!-- Brand -->
    <div class="sidebar-brand">
      <div class="sidebar-logo">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L4 6V12C4 16.5 7 20.5 12 22C17 20.5 20 16.5 20 12V6L12 2Z" fill="white" fill-opacity="0.15" stroke="white" stroke-width="1.8" stroke-linejoin="round"/>
          <path d="M8.5 12L11 14.5L15.5 9.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <span class="sidebar-brand-text">LexAd</span>
    </div>
    <p class="sidebar-slogan">智能合规 · 广告无忧</p>

    <!-- Main nav -->
    <nav class="sidebar-nav" aria-label="主导航">
      <router-link
        v-for="item in mainItems"
        :key="item.route"
        :to="item.route"
        :title="item.label"
        :aria-label="item.label"
        :class="{ active: isActive(item.route) }"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <template v-if="item.icon === 'home'">
            <path d="M3 12l9-9 9 9M5 10v10h14V10" stroke-linecap="round" stroke-linejoin="round"/>
          </template>
          <template v-else-if="item.icon === 'submit'">
            <path d="M12 5v14M5 12h14" stroke-linecap="round"/>
          </template>
          <template v-else-if="item.icon === 'legal'">
            <path d="M3 6l9-3 9 3M3 6v12l9 3 9-3V6M3 6l9 3 9-3M12 9v12" stroke-linecap="round" stroke-linejoin="round"/>
          </template>
          <template v-else-if="item.icon === 'brand'">
            <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2v16z" stroke-linecap="round" stroke-linejoin="round"/>
          </template>
          <template v-else-if="item.icon === 'knowledge'">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" stroke-linecap="round" stroke-linejoin="round"/>
          </template>
          <template v-else>
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" stroke-linecap="round" stroke-linejoin="round"/>
          </template>
        </svg>
        <span class="sidebar-nav-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- Knowledge nav (secondary group) -->
    <nav v-if="knowledgeItems.length" class="sidebar-nav sidebar-nav-secondary" aria-label="资料导航">
      <router-link
        v-for="item in knowledgeItems"
        :key="item.route"
        :to="item.route"
        :title="item.label"
        :aria-label="item.label"
        :class="{ active: isActive(item.route) }"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <template v-if="item.icon === 'admin'">
            <path d="M4 7h16M6 7v12h12V7M9 11h6M9 15h4M8 4h8l1 3H7l1-3Z" stroke-linecap="round" stroke-linejoin="round"/>
          </template>
          <template v-else>
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" stroke-linecap="round" stroke-linejoin="round"/>
          </template>
        </svg>
        <span class="sidebar-nav-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- Footer -->
    <div class="sidebar-footer">
      <span class="sidebar-version">v{{ APP_VERSION }}</span>
    </div>
  </aside>
</template>
