<script setup lang="ts">
import { computed } from 'vue'
import type { BrandProfile } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'

const props = withDefaults(defineProps<{
  profile: BrandProfile | null
  loading: boolean
  mode?: 'compact' | 'full'
}>(), { mode: 'compact' })

const memory = computed(() => props.profile?.memory_impression)
const statusVariant = computed<'success' | 'warning' | 'danger' | 'gray'>(() => ({
  stable: 'success',
  mixed: 'warning',
  attention: 'danger',
  collecting: 'gray',
}[memory.value?.status || 'collecting'] as 'success' | 'warning' | 'danger' | 'gray'))

const summaryClass = computed(() => ({
  stable: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200',
  mixed: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200',
  attention: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200',
  collecting: 'border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200',
}[memory.value?.status || 'collecting']))
</script>

<template>
  <div v-if="profile || loading" class="brand-memory-card" :class="{ 'brand-memory-card-full': mode === 'full' }">
    <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
      <div class="flex items-start gap-2">
        <svg class="mt-0.5 shrink-0" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="var(--color-brand)" stroke-width="2"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <div>
          <p class="text-xs font-semibold text-gray-500 dark:text-gray-400">品牌现有记忆印象</p>
          <p class="mt-1 text-[11px] text-gray-400">历史参考 · 不参与本次自动审查评分</p>
        </div>
      </div>
      <StatusBadge v-if="profile && memory" :variant="statusVariant">{{ memory.headline }}</StatusBadge>
    </div>

    <div v-if="loading" class="animate-pulse space-y-2">
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
      <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
      <div v-if="mode === 'full'" class="h-20 bg-gray-100 dark:bg-gray-800 rounded"></div>
    </div>

    <template v-else-if="profile && memory">
      <div v-if="mode === 'compact'" class="space-y-2 text-sm">
        <p class="rounded-lg border px-3 py-2 text-xs leading-5" :class="summaryClass">{{ memory.summary }}</p>
        <div v-if="memory.industries.length" class="flex justify-between gap-3">
          <span class="text-gray-500 dark:text-gray-400">常用行业</span>
          <span class="text-right text-gray-800 dark:text-gray-200">{{ memory.industries.join('、') }}</span>
        </div>
        <div class="flex justify-between gap-3">
          <span class="text-gray-500 dark:text-gray-400">记忆样本</span>
          <span class="font-medium text-gray-800 dark:text-gray-200">{{ memory.decided_review_count }} 次法务决定</span>
        </div>
        <div class="flex justify-between gap-3">
          <span class="text-gray-500 dark:text-gray-400">通过率</span>
          <span :class="profile.pass_rate !== null && profile.pass_rate >= 80 ? 'text-emerald-600 dark:text-emerald-400' : profile.pass_rate !== null ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400'" class="font-medium">
            {{ profile.pass_rate !== null ? profile.pass_rate.toFixed(0) + '%' : '-' }}
          </span>
        </div>
        <div v-if="memory.frequent_risks.length" class="pt-2 border-t border-gray-100 dark:border-gray-700">
          <p class="text-xs text-gray-400 mb-1">高频风险记忆</p>
          <div class="flex flex-wrap gap-1">
            <span v-for="item in memory.frequent_risks.slice(0, 3)" :key="item.text" class="badge badge-danger">{{ item.text }}</span>
          </div>
        </div>
      </div>

      <div v-else class="space-y-5">
        <div class="rounded-xl border px-4 py-3 text-sm leading-6" :class="summaryClass">
          <p class="font-semibold">{{ memory.headline }}</p>
          <p class="mt-1">{{ memory.summary }}</p>
        </div>

        <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <div class="rounded-xl bg-gray-50 p-3 dark:bg-gray-800">
            <p class="text-xs text-gray-400">完成审核</p>
            <p class="mt-1 text-xl font-bold text-gray-800 dark:text-gray-100">{{ memory.completed_review_count }}</p>
          </div>
          <div class="rounded-xl bg-gray-50 p-3 dark:bg-gray-800">
            <p class="text-xs text-gray-400">法务决定</p>
            <p class="mt-1 text-xl font-bold text-gray-800 dark:text-gray-100">{{ memory.decided_review_count }}</p>
          </div>
          <div class="rounded-xl bg-gray-50 p-3 dark:bg-gray-800">
            <p class="text-xs text-gray-400">历史通过率</p>
            <p class="mt-1 text-xl font-bold text-gray-800 dark:text-gray-100">{{ profile.pass_rate !== null ? profile.pass_rate.toFixed(0) + '%' : '-' }}</p>
          </div>
          <div class="rounded-xl bg-gray-50 p-3 dark:bg-gray-800">
            <p class="text-xs text-gray-400">平均提交轮次</p>
            <p class="mt-1 text-xl font-bold text-gray-800 dark:text-gray-100">{{ memory.avg_versions !== null ? memory.avg_versions.toFixed(1) : '-' }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div class="rounded-xl border border-gray-200 p-4 dark:border-gray-700">
            <p class="text-xs text-gray-400">最近五次法务倾向</p>
            <div class="mt-3 flex flex-wrap gap-2 text-sm">
              <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">通过 {{ memory.recent_decisions.approved }}</span>
              <span class="rounded-full bg-amber-50 px-2.5 py-1 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">条件 {{ memory.recent_decisions.conditional }}</span>
              <span class="rounded-full bg-red-50 px-2.5 py-1 text-red-700 dark:bg-red-950/40 dark:text-red-300">退回 {{ memory.recent_decisions.returned }}</span>
            </div>
          </div>
          <div class="rounded-xl border border-gray-200 p-4 dark:border-gray-700">
            <p class="text-xs text-gray-400">历史修改成本</p>
            <p class="mt-3 text-sm font-medium text-gray-800 dark:text-gray-100">{{ memory.revision_tendency }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div class="rounded-xl border border-gray-200 p-4 dark:border-gray-700">
            <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200">高频风险记忆</h4>
            <div v-if="memory.frequent_risks.length" class="mt-3 space-y-2">
              <div v-for="item in memory.frequent_risks" :key="item.text" class="flex items-center justify-between gap-3 text-sm">
                <span class="text-gray-700 dark:text-gray-300">{{ item.text }}</span>
                <span class="text-xs text-gray-400">{{ item.count }} 次</span>
              </div>
            </div>
            <p v-else class="mt-3 text-sm text-gray-400">尚无高频风险记录</p>
          </div>
          <div class="rounded-xl border border-gray-200 p-4 dark:border-gray-700">
            <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200">常见修改建议</h4>
            <div v-if="memory.common_suggestions.length" class="mt-3 space-y-2">
              <div v-for="item in memory.common_suggestions" :key="item.text" class="flex items-start justify-between gap-3 text-sm">
                <span class="text-gray-700 dark:text-gray-300">{{ item.text }}</span>
                <span class="shrink-0 text-xs text-gray-400">{{ item.count }} 次</span>
              </div>
            </div>
            <p v-else class="mt-3 text-sm text-gray-400">尚无可复用的修改建议</p>
          </div>
        </div>

        <div v-if="memory.industries.length" class="border-t border-gray-100 pt-4 dark:border-gray-700">
          <p class="text-xs text-gray-400">管理员确认的常用行业</p>
          <div class="mt-2 flex flex-wrap gap-2">
            <span v-for="industry in memory.industries" :key="industry" class="rounded-full bg-sky-50 px-2.5 py-1 text-xs text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{{ industry }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
