<script setup lang="ts">
import type { BrandProfile } from '@/types'

defineProps<{
  profile: BrandProfile | null
  loading: boolean
}>()
</script>

<template>
  <div v-if="profile || loading" class="brand-memory-card">
    <div class="flex items-center gap-2 mb-3">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand)" stroke-width="2"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span class="text-xs font-semibold text-gray-500">品牌历史参考 · 不参与本次 AI 风险评分</span>
    </div>

    <div v-if="loading" class="animate-pulse space-y-2">
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
      <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
    </div>

    <div v-else-if="profile" class="space-y-2 text-sm">
      <div v-if="profile.brand.industries?.length" class="flex justify-between gap-3">
        <span class="text-gray-500">常用行业</span>
        <span class="text-right text-gray-800 dark:text-gray-200">{{ profile.brand.industries.join('、') }}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-gray-500">审核次数</span>
        <span class="font-medium text-gray-800 dark:text-gray-200">{{ profile.total_reviews }}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-gray-500">通过率</span>
        <span :class="profile.pass_rate !== null && profile.pass_rate >= 80 ? 'text-green-600' : profile.pass_rate !== null ? 'text-amber-600' : 'text-gray-400'" class="font-medium">
          {{ profile.pass_rate !== null ? profile.pass_rate.toFixed(0) + '%' : '-' }}
        </span>
      </div>
      <div v-if="profile.top_violations?.length" class="pt-2 border-t border-gray-100 dark:border-gray-700">
        <p class="text-xs text-gray-400 mb-1">高频违规</p>
        <div class="flex flex-wrap gap-1">
          <span v-for="v in profile.top_violations.slice(0, 5)" :key="v.rule_id" class="badge badge-danger">{{ v.rule_text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
