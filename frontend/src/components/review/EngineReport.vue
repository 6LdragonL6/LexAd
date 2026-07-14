<script setup lang="ts">
import { computed } from 'vue'
import type { EngineResult } from '@/types'

const props = defineProps<{ result: EngineResult }>()

const layers = computed(() => [props.result.layer1, props.result.layer2, props.result.layer3, props.result.layer4])
const hitCount = computed(() => props.result.hit_count ?? layers.value.reduce((count, layer) => count + layer.matched_rules.length, 0))

function statusText(status?: string) {
  return status === 'matched' ? '已有确认结果' : status === 'unavailable' ? '待人工复核' : status === 'failed' ? '执行失败' : '未发现明确风险'
}

function riskLabel(value?: string) {
  return ({ high: '高风险', medium: '中风险', low: '低风险' } as Record<string, string>)[value || ''] || '已确认风险'
}

function riskTypeLabel(value?: string) {
  return ({ high: '高风险问题', medium: '中风险问题', low: '低风险问题', severe: '严重风险问题' } as Record<string, string>)[value || ''] || value || '合规风险'
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">审查引擎·执行报告</h3>
      <span class="text-xs rounded-full bg-red-50 text-red-600 px-2 py-1">{{ hitCount }} 项确认问题</span>
    </div>
    <details v-for="layer in layers" :key="layer.layer" :open="layer.status === 'matched' || layer.matched_rules.length > 0" class="text-sm rounded-lg border border-gray-200 dark:border-gray-700 px-3">
      <summary class="font-medium text-gray-600 dark:text-gray-300 cursor-pointer py-3 flex items-center justify-between gap-3">
        <span>{{ layer.layer }}</span>
        <span class="text-xs" :class="layer.status === 'matched' || layer.matched_rules.length ? 'text-red-600' : layer.status === 'unavailable' || layer.status === 'failed' ? 'text-amber-600' : 'text-gray-400'">{{ statusText(layer.status || (layer.matched_rules.length ? 'matched' : 'no_match')) }}</span>
      </summary>
      <div v-if="layer.status === 'unavailable' || layer.status === 'failed'" class="pb-3 text-amber-700 text-sm">
        {{ layer.explanations.join('；') || '该模块未能给出可用结果，这不是低风险结论。' }}
      </div>
      <div v-else class="pb-3 space-y-2">
        <p v-for="exp in layer.explanations" :key="exp" class="text-gray-500 dark:text-gray-400">{{ exp }}</p>
        <div v-for="rule in layer.matched_rules" :key="rule.rule_id" class="rounded-md bg-red-50 dark:bg-red-900/20 p-3">
          <div class="flex items-center justify-between gap-3">
            <p class="font-medium text-red-700 dark:text-red-300">{{ riskTypeLabel(rule.match_type) }}</p>
            <span class="text-xs text-red-600">{{ rule.risk_level_label || riskLabel(rule.risk_level) }} · AI 已确认</span>
          </div>
          <p class="text-sm text-gray-700 dark:text-gray-300 mt-2">原文证据：“{{ rule.evidence_quote || rule.rule_text }}”</p>
          <p v-if="rule.reasoning || rule.explanation" class="text-xs text-gray-500 mt-1">判断理由：{{ rule.reasoning || rule.explanation }}</p>
          <p v-if="rule.source_law" class="text-xs text-gray-400 mt-1">资料来源：{{ rule.source_law }}</p>
          <p v-if="rule.suggestion" class="text-xs text-sky-600 mt-1">修改建议：{{ rule.suggestion }}</p>
        </div>
        <div v-for="item in layer.verification_items || []" :key="item.item_id" class="rounded-md bg-amber-50 dark:bg-amber-900/20 p-3">
          <p class="font-medium text-amber-700">{{ item.verification_type }} · 需核验资料</p>
          <p class="text-sm text-gray-700 mt-2">原文声明：“{{ item.evidence_quote }}”</p>
          <p class="text-xs text-gray-500 mt-1">{{ item.reason }}</p>
        </div>
      </div>
    </details>
    <div class="border-t pt-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">修改建议</h4>
      <ul class="text-sm text-gray-600 space-y-1">
        <li v-for="s in result.suggestions" :key="s" class="flex items-start gap-1">
          <span class="text-sky-500">-</span> {{ s }}
        </li>
      </ul>
    </div>
  </div>
</template>
