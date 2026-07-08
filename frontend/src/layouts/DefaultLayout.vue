<script setup lang="ts">
import TopBar from '@/components/layout/TopBar.vue'
</script>

<template>
  <div class="app-page">
    <TopBar />
    <div class="flex-1 overflow-auto">
      <slot />
    </div>
  </div>
</template>
