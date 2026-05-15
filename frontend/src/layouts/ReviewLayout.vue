<script setup lang="ts">
import TopBar from '@/components/layout/TopBar.vue'
import ThreeColLayout from '@/components/layout/ThreeColLayout.vue'
</script>

<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <TopBar />
    <div class="flex-1 overflow-hidden">
      <ThreeColLayout>
        <template #left><slot name="left" /></template>
        <template #center><slot name="center" /></template>
        <template #right><slot name="right" /></template>
      </ThreeColLayout>
    </div>
  </div>
</template>
