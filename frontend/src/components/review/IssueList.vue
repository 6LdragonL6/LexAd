<script setup lang="ts">
import type { MatchedRule } from '@/types'

defineProps<{ issues: MatchedRule[] }>()
const emit = defineEmits<{ select: [rule: MatchedRule] }>()

function riskLabel(issue: MatchedRule) {
  if (issue.risk_level_label) return issue.risk_level_label
  return ({ high: '高风险', medium: '中风险', low: '低风险' } as Record<string, string>)[issue.risk_level || issue.match_type] || '已确认风险'
}

function riskType(value: string) {
  return ({ high: '高风险问题', medium: '中风险问题', low: '低风险问题' } as Record<string, string>)[value] || value
}
</script>

<template>
  <div class="space-y-2">
    <h3 class="text-sm font-semibold text-gray-700 mb-3">问题清单 ({{ issues.length }})</h3>
    <div v-for="issue in issues" :key="issue.rule_id"
      @click="emit('select', issue)"
      class="p-2 rounded-lg text-sm cursor-pointer hover:bg-gray-100 border border-transparent hover:border-gray-300"
      :class="{
        'border-red-200 bg-red-50': issue.risk_level === 'high' || issue.match_type === 'high',
        'border-orange-200 bg-orange-50': issue.risk_level === 'medium' || issue.match_type === 'medium',
        'border-sky-200 bg-sky-50': issue.risk_level === 'low' || issue.match_type === 'low',
      }">
      <span class="text-xs px-1.5 py-0.5 rounded mr-1.5"
        :class="{
          'bg-red-100 text-red-700': issue.risk_level === 'high' || issue.match_type === 'high',
          'bg-orange-100 text-orange-700': issue.risk_level === 'medium' || issue.match_type === 'medium',
          'bg-sky-100 text-sky-700': issue.risk_level === 'low' || issue.match_type === 'low',
        }">{{ riskLabel(issue) }}</span>
      <span class="text-gray-700">{{ riskType(issue.match_type) }}：{{ issue.evidence_quote || issue.rule_text }}</span>
    </div>
    <p v-if="!issues.length" class="text-sm text-gray-400">未发现问题</p>
  </div>
</template>
