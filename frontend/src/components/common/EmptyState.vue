<script setup lang="ts">
defineProps<{ message: string }>()
</script>

<template>
  <div class="text-center py-12">
    <p class="text-muted mb-4">{{ message }}</p>
    <slot name="action" />
  </div>
</template>
