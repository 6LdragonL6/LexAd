<script setup lang="ts">
import type { EngineResult } from '@/types'

defineProps<{ result: EngineResult; materialName: string }>()
</script>

<template>
  <div class="text-sm space-y-3">
    <h3 class="font-semibold text-gray-700">{{ materialName }}</h3>
    <div class="p-3 bg-sky-50 rounded-lg">
      <p class="font-medium text-sky-800">摘要</p>
      <p class="text-sky-700 mt-1 whitespace-pre-wrap">{{ result.summary }}</p>
    </div>
  </div>
</template>
