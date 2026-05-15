<script setup lang="ts">
import TopBar from '@/components/layout/TopBar.vue'
</script>

<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <TopBar />
    <div class="flex-1 overflow-hidden">
      <slot />
    </div>
  </div>
</template>
