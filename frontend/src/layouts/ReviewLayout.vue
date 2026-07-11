<script setup lang="ts">
import AppShell from '@/layouts/AppShell.vue'
import ThreeColLayout from '@/components/layout/ThreeColLayout.vue'
</script>

<template>
  <AppShell>
    <ThreeColLayout>
      <template #left><slot name="left" /></template>
      <template #center><slot name="center" /></template>
      <template #right><slot name="right" /></template>
    </ThreeColLayout>
  </AppShell>
</template>
