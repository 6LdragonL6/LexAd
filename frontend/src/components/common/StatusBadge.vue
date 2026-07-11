<script setup lang="ts">
defineProps<{ variant: 'success' | 'warning' | 'danger' | 'info' | 'gray' }>()
</script>

<template>
  <span :class="`badge badge-${variant}`">
    <slot />
  </span>
</template>
