<script setup lang="ts">
defineProps<{ score: number }>()
</script>

<template>
  <div class="text-center mb-6">
    <div class="text-5xl font-bold" :class="{
      'text-green-500': score >= 80,
      'text-yellow-500': score >= 50 && score < 80,
      'text-red-500': score < 50,
    }">{{ score }}</div>
    <p class="text-sm text-gray-400 mt-1">风险评分 / 100</p>
    <div class="w-full bg-gray-200 rounded-full h-2 mt-3">
      <div class="h-2 rounded-full transition-all" :class="{
        'bg-green-500': score >= 80,
        'bg-yellow-500': score >= 50 && score < 80,
        'bg-red-500': score < 50,
      }" :style="{ width: score + '%' }"></div>
    </div>
  </div>
</template>
