<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import TopBar from '@/components/layout/TopBar.vue'
import MobileNavigation from '@/components/layout/MobileNavigation.vue'
</script>

<template>
  <div class="app-shell">
    <AppSidebar class="app-shell-sidebar" />
    <div class="app-shell-main">
      <MobileNavigation />
      <TopBar />
      <main class="app-shell-content">
        <slot />
      </main>
    </div>
  </div>
</template>
