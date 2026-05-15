<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import ReviewLayout from '@/layouts/ReviewLayout.vue'
import ScoreBox from '@/components/review/ScoreBox.vue'
import IssueList from '@/components/review/IssueList.vue'
import EngineReport from '@/components/review/EngineReport.vue'
import SummaryPanel from '@/components/review/SummaryPanel.vue'
import type { Material, Review, MatchedRule } from '@/types'

const route = useRoute()
const router = useRouter()
const material = ref<Material | null>(null)
const review = ref<Review | null>(null)
const loading = ref(true)
const selectedRule = ref<MatchedRule | null>(null)
const highlightText = ref('')

function getAllIssues(): MatchedRule[] {
  if (!review.value) return []
  const r = review.value.ai_result
  return [...r.layer1.matched_rules, ...r.layer2.matched_rules, ...r.layer3.matched_rules]
}

function getHighlightedHtml(): string {
  if (!material.value) return ''
  let text = material.value.raw_text
  const allIssues = getAllIssues()
  for (const issue of allIssues) {
    const cls = issue === selectedRule.value ? 'highlight-active' : 'highlight'
    const colorMap: Record<string, string> = {
      '绝对化用语': '#ef4444', '涉医用语': '#ef4444', 'high': '#ef4444',
      '效果保证': '#f97316', '功效宣称': '#f97316', 'medium': '#f97316',
      '需证明材料': '#3b82f6',
    }
    const color = colorMap[issue.match_type] || '#6b7280'
    text = text.replace(issue.rule_text, `<mark data-rule-id="${issue.rule_id}" style="background:${color}20;border-bottom:2px solid ${color};cursor:pointer" class="px-0.5 rounded">${issue.rule_text}</mark>`)
  }
  return text
}

onMounted(async () => {
  const reviewId = route.params.id as string
  const rRes = await reviewsApi.get(reviewId)
  review.value = rRes.data
  const mRes = await materialsApi.get(rRes.data.material_id)
  material.value = mRes.data
  loading.value = false
})
</script>

<template>
  <ReviewLayout v-if="!loading && material && review">
    <template #left>
      <ScoreBox :score="review.ai_risk_score" />
      <IssueList :issues="getAllIssues()" @select="selectedRule = $event" />
      <div class="mt-6 space-y-2">
        <button class="btn-primary w-full text-sm" @click="router.push(`/legal/${review.id}`)">提交法务审核</button>
        <button class="btn-outline w-full text-sm" @click="router.push(`/submit`)">重新编辑</button>
      </div>
    </template>
    <template #center>
      <SummaryPanel :result="review.ai_result" :material-name="material.name" />
      <div class="mt-4 p-4 bg-white rounded-lg border text-sm leading-relaxed" v-html="highlightText || getHighlightedHtml()" />
    </template>
    <template #right>
      <EngineReport :result="review.ai_result" />
    </template>
  </ReviewLayout>
  <div v-else-if="loading" class="flex items-center justify-center h-screen">
    <p class="text-gray-500">审查进行中，请稍候...</p>
  </div>
</template>
