<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>

<template>
  <div class="mb-6">
    <h2 class="page-heading">{{ title }}</h2>
    <p v-if="description" class="text-sm text-muted mt-1">{{ description }}</p>
  </div>
</template>
