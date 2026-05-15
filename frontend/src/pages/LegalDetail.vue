<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import { useUserStore } from '@/stores/user'
import ReviewLayout from '@/layouts/ReviewLayout.vue'
import ScoreBox from '@/components/review/ScoreBox.vue'
import IssueList from '@/components/review/IssueList.vue'
import EngineReport from '@/components/review/EngineReport.vue'
import type { Material, Review, MatchedRule } from '@/types'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const material = ref<Material | null>(null)
const review = ref<Review | null>(null)
const loading = ref(true)
const decision = ref('approved')
const notes = ref('')
const returnReasons = ref('')
const submitting = ref(false)

function getAllIssues(): MatchedRule[] {
  if (!review.value) return []
  const r = review.value.ai_result
  return [...r.layer1.matched_rules, ...r.layer2.matched_rules, ...r.layer3.matched_rules]
}

onMounted(async () => {
  const reviewId = route.params.id as string
  const rRes = await reviewsApi.get(reviewId)
  review.value = rRes.data
  const mRes = await materialsApi.get(rRes.data.material_id)
  material.value = mRes.data
  loading.value = false
})

async function handleDecision() {
  if (!review.value) return
  submitting.value = true
  try {
    await reviewsApi.submitDecision(review.value.id, {
      decision: decision.value,
      notes: notes.value,
      return_reasons: returnReasons.value,
    })
    router.push('/legal')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <ReviewLayout v-if="!loading && material && review">
    <template #left>
      <ScoreBox :score="review.ai_risk_score" />
      <IssueList :issues="getAllIssues()" />
    </template>
    <template #center>
      <div class="bg-white rounded-lg border p-4 mb-4">
        <h3 class="font-semibold mb-2">{{ material.name }}</h3>
        <p class="text-sm text-gray-600 whitespace-pre-wrap">{{ material.raw_text }}</p>
        <div class="flex gap-2 mt-2 text-xs text-gray-400">
          <span>{{ material.industry }}</span>
          <span>{{ material.platforms.join(', ') }}</span>
        </div>
      </div>
    </template>
    <template #right>
      <EngineReport :result="review.ai_result" />
      <div v-if="store.isLegal && review.legal_decision === null" class="mt-6 card">
        <h3 class="font-semibold mb-3">法务审核决定</h3>
        <div class="space-y-3">
          <div class="flex gap-3">
            <label class="flex items-center gap-1 text-sm">
              <input type="radio" v-model="decision" value="approved" /> 通过
            </label>
            <label class="flex items-center gap-1 text-sm">
              <input type="radio" v-model="decision" value="returned" /> 退回
            </label>
            <label class="flex items-center gap-1 text-sm">
              <input type="radio" v-model="decision" value="conditional" /> 有条件通过
            </label>
          </div>
          <div v-if="decision !== 'approved'">
            <label class="block text-sm font-medium mb-1">退回原因</label>
            <textarea v-model="returnReasons" class="input h-20" placeholder="请说明退回或条件..."></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">法务备注</label>
            <textarea v-model="notes" class="input h-20" placeholder="内部备注..."></textarea>
          </div>
          <button @click="handleDecision" :disabled="submitting" class="btn-primary w-full">
            {{ submitting ? '提交中...' : '提交决定' }}
          </button>
        </div>
      </div>
      <div v-else-if="review.legal_decision" class="mt-6 card">
        <h3 class="font-semibold mb-2">审核结果</h3>
        <p :class="{
          'text-green-600': review.legal_decision === 'approved',
          'text-red-600': review.legal_decision === 'returned',
          'text-yellow-600': review.legal_decision === 'conditional',
        }" class="font-bold">
          {{ review.legal_decision === 'approved' ? '✅ 已通过' : review.legal_decision === 'returned' ? '❌ 已退回' : '⚠️ 有条件通过' }}
        </p>
        <p v-if="review.return_reasons" class="text-sm text-gray-600 mt-2">{{ review.return_reasons }}</p>
        <p v-if="review.legal_notes" class="text-sm text-gray-500 mt-1">备注: {{ review.legal_notes }}</p>
      </div>
    </template>
  </ReviewLayout>
  <div v-else class="flex items-center justify-center h-screen text-gray-500">加载中...</div>
</template>
