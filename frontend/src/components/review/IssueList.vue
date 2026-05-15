<script setup lang="ts">
import type { MatchedRule } from '@/types'

defineProps<{ issues: MatchedRule[] }>()
const emit = defineEmits<{ select: [rule: MatchedRule] }>()
</script>

<template>
  <div class="space-y-2">
    <h3 class="text-sm font-semibold text-gray-700 mb-3">问题清单 ({{ issues.length }})</h3>
    <div v-for="issue in issues" :key="issue.rule_id"
      @click="emit('select', issue)"
      class="p-2 rounded-lg text-sm cursor-pointer hover:bg-gray-100 border border-transparent hover:border-gray-300"
      :class="{
        'border-red-200 bg-red-50': issue.match_type === '绝对化用语' || issue.match_type === '涉医用语' || issue.match_type === 'high',
        'border-orange-200 bg-orange-50': issue.match_type === '效果保证' || issue.match_type === '功效宣称' || issue.match_type === 'medium',
        'border-blue-200 bg-blue-50': issue.match_type === '需证明材料',
      }">
      <span class="text-xs px-1.5 py-0.5 rounded mr-1.5"
        :class="{
          'bg-red-100 text-red-700': issue.match_type === '绝对化用语' || issue.match_type === '涉医用语' || issue.match_type === 'high',
          'bg-orange-100 text-orange-700': issue.match_type === '效果保证' || issue.match_type === '功效宣称' || issue.match_type === 'medium',
          'bg-blue-100 text-blue-700': issue.match_type === '需证明材料',
          'bg-gray-100 text-gray-600': !['绝对化用语', '涉医用语', 'high', '效果保证', '功效宣称', 'medium', '需证明材料'].includes(issue.match_type),
        }">{{ issue.match_type }}</span>
      <span class="text-gray-700">{{ issue.rule_text }}</span>
    </div>
    <p v-if="!issues.length" class="text-sm text-gray-400">未发现问题</p>
  </div>
</template>
