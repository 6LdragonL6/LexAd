<script setup lang="ts">
defineProps<{ message: string }>()
</script>

<template>
  <div class="text-center py-12">
    <p class="text-muted">{{ message }}</p>
  </div>
</template>
