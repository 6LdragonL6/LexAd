<script setup lang="ts">
import { computed } from 'vue'
import type { Review } from '@/types'
import StatusBadge from '@/components/common/StatusBadge.vue'
import HistoricalConsequencePanel from '@/components/review/HistoricalConsequencePanel.vue'

const props = withDefaults(defineProps<{ review: Review; mode?: 'summary' | 'full' }>(), { mode: 'full' })

const result = computed<Record<string, any>>(() => props.review.public_opinion_result || {})
const status = computed(() => result.value.status === 'manual_review'
  ? 'manual_review'
  : props.review.public_opinion_module_status || 'unavailable')

const statusLabel = computed(() => ({
  pending: '等待中', running: '分析中', succeeded: '已完成', failed: '执行失败',
  unavailable: '不可用', manual_review: '待人工复核',
} as Record<string, string>)[status.value] || status.value)

const riskLabel = computed(() => ({
  low: '低', medium: '中', high: '高', severe: '严重', uncertain: '不确定', unavailable: '资料库待补充',
} as Record<string, string>)[result.value.risk_level || 'unavailable'] || '不确定')

const riskClass = computed(() => {
  if (['severe', 'high'].includes(result.value.risk_level)) return 'border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300'
  if (result.value.risk_level === 'medium') return 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-900 dark:bg-orange-950/30 dark:text-orange-300'
  if (result.value.risk_level === 'low') return 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300'
  return 'border-gray-200 bg-gray-50 text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300'
})

const badgeVariant = computed<'success' | 'warning' | 'danger' | 'info' | 'gray'>(() => {
  if (status.value === 'succeeded') return 'success'
  if (status.value === 'failed') return 'danger'
  if (status.value === 'pending' || status.value === 'running' || status.value === 'manual_review') return 'warning'
  return 'gray'
})

const sourceLabel = computed(() => ({ local: '资料候选', ai: 'AI 语义裁决', hybrid: 'AI 与资料库' } as Record<string, string>)[result.value.assessment_source] || '证据不足')
const verificationLabel = (value?: string) => ({ verified: '已核验', needs_review: '待复核', unverified: '未核验' } as Record<string, string>)[value || ''] || value || '待复核'
</script>

<template>
  <section v-if="mode === 'summary'" class="card border-l-4 border-l-purple-500">
    <div class="flex items-start justify-between gap-3">
      <div>
        <p class="text-sm text-gray-500 dark:text-gray-400">舆情风险</p>
        <p class="mt-2 text-3xl font-bold" :class="riskLabel === '低' ? 'text-emerald-600 dark:text-emerald-400' : riskLabel === '高' || riskLabel === '严重' ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'">{{ riskLabel }}</p>
        <p class="mt-1 text-xs text-gray-400">{{ result.risk_score ?? '-' }}/100 · {{ sourceLabel }} · 不计入法律合规分</p>
      </div>
      <StatusBadge :variant="badgeVariant">{{ statusLabel }}</StatusBadge>
    </div>
    <div class="mt-4 rounded-lg border px-3 py-2 text-sm" :class="riskClass">
      {{ result.explanation || result.message || '暂无舆情分析说明' }}
    </div>
  </section>

  <section v-else class="card public-opinion-report">
    <div class="flex flex-wrap items-start justify-between gap-3 border-b border-gray-100 pb-4 dark:border-gray-700">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wider text-purple-500 dark:text-purple-300">Public opinion</p>
        <h3 class="mt-1 font-semibold text-gray-800 dark:text-gray-100">舆情审核</h3>
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">独立风险轴，不计入法律合规分</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="rounded-full border px-2.5 py-1 text-sm font-semibold" :class="riskClass">{{ riskLabel }}风险</span>
        <StatusBadge :variant="badgeVariant">{{ statusLabel }}</StatusBadge>
      </div>
    </div>

    <div v-if="status === 'failed' || status === 'unavailable' || result.requires_manual_review" class="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
      <p class="font-semibold">待人工复核</p>
      <p class="mt-1">{{ review.public_opinion_module_error || result.disagreement_reason || result.message || '舆情模块未能给出可直接采用的结论。' }}</p>
    </div>

    <div class="mt-4 rounded-xl border px-4 py-3 text-sm leading-6" :class="riskClass">
      {{ result.explanation || result.message || '暂无舆情分析说明' }}
    </div>

    <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div class="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
        <p class="text-xs text-gray-400">风险议题</p>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-200">{{ result.risk_topics?.join('、') || '暂无' }}</p>
      </div>
      <div class="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
        <p class="text-xs text-gray-400">受影响群体</p>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-200">{{ result.affected_groups?.join('、') || '暂无' }}</p>
      </div>
      <div class="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
        <p class="text-xs text-gray-400">传播诱因</p>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-200">{{ result.propagation_drivers?.join('、') || '暂无' }}</p>
      </div>
      <div class="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
        <p class="text-xs text-gray-400">置信度与来源</p>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-200">{{ result.confidence ?? '-' }}<span v-if="result.confidence !== undefined">%</span> · {{ sourceLabel }}</p>
      </div>
    </div>

    <div v-if="result.evidence_quotes?.length" class="mt-5">
      <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200">原文证据</h4>
      <div class="mt-2 flex flex-wrap gap-2">
        <span v-for="quote in result.evidence_quotes" :key="quote" class="rounded-lg bg-purple-50 px-3 py-1.5 text-sm text-purple-700 dark:bg-purple-950/40 dark:text-purple-200">“{{ quote }}”</span>
      </div>
    </div>

    <div v-if="result.similar_events?.length" class="mt-5">
      <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200">相似舆情事件</h4>
      <div class="mt-3 space-y-3">
        <div v-for="event in result.similar_events" :key="event.event_id" class="rounded-xl border border-gray-200 p-4 dark:border-gray-700">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <span class="font-medium text-gray-800 dark:text-gray-100">{{ event.title || event.event_title }}</span>
            <span class="text-xs text-gray-400">AI 确认相似 · {{ verificationLabel(event.verification_status) }}</span>
          </div>
          <HistoricalConsequencePanel :value="event.historical_consequence" />
        </div>
      </div>
    </div>

    <div v-if="result.suggestions?.length" class="mt-5">
      <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200">舆情修改建议</h4>
      <ul class="mt-2 space-y-2 text-sm text-gray-600 dark:text-gray-300">
        <li v-for="suggestion in result.suggestions" :key="suggestion" class="flex gap-2"><span class="text-purple-500">•</span><span>{{ suggestion }}</span></li>
      </ul>
    </div>
  </section>
</template>
