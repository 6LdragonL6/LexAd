<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import { useUserStore } from '@/stores/user'
import ReviewLayout from '@/layouts/ReviewLayout.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BrandMemoryCard from '@/components/brand/BrandMemoryCard.vue'
import ReviewHistoryDrawer from '@/components/review/ReviewHistoryDrawer.vue'
import EngineReport from '@/components/review/EngineReport.vue'
import { brandsApi } from '@/api/brands'
import type { Material, Review, MatchedRule, BrandProfile, MaterialVersion } from '@/types'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const material = ref<Material | null>(null)
const review = ref<Review | null>(null)
const loading = ref(true)
const versions = ref<MaterialVersion[]>([])
const showVersions = ref(false)
const selectedVersion = ref<MaterialVersion | null>(null)
const selectedReview = ref<Review | null>(null)
const historyLoading = ref(false)
const decision = ref('approved')
const notes = ref('')
const returnReasons = ref('')
const submitting = ref(false)
const decisionError = ref('')
const brandProfile = ref<BrandProfile | null>(null)
const brandProfileLoading = ref(false)

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
  try {
    const vRes = await materialsApi.versions(rRes.data.material_id)
    versions.value = vRes.data.versions || []
  } catch {
    versions.value = []
  }
  loading.value = false

  if (material.value?.brand_id) {
    brandProfileLoading.value = true
    try {
      const profileRes = await brandsApi.profile(material.value.brand_id)
      brandProfile.value = profileRes.data
    } catch {
      brandProfile.value = null
    } finally {
      brandProfileLoading.value = false
    }
  }
})

async function handleDecision() {
  if (!review.value) return
  submitting.value = true
  decisionError.value = ''
  try {
    await reviewsApi.submitDecision(review.value.id, {
      decision: decision.value,
      notes: notes.value,
      return_reasons: returnReasons.value,
    })
    router.push('/legal')
  } catch (error: any) {
    decisionError.value = error.response?.data?.detail || '法务决定提交失败'
  } finally {
    submitting.value = false
  }
}

async function openHistory(version: MaterialVersion) {
  selectedVersion.value = version
  selectedReview.value = null
  historyLoading.value = true
  try {
    selectedReview.value = (await reviewsApi.get(version.review_id)).data
  } finally {
    historyLoading.value = false
  }
}
</script>

<template>
  <ReviewLayout v-if="!loading && material && review">
    <template #left>
      <div class="text-center mb-6">
        <div class="text-5xl font-bold" :class="{
          'text-green-500': review.ai_risk_score >= 80,
          'text-yellow-500': review.ai_risk_score >= 50 && review.ai_risk_score < 80,
          'text-red-500': review.ai_risk_score < 50,
        }">{{ review.ai_risk_score }}</div>
        <p class="text-sm text-gray-400 mt-1">风险评分 / 100</p>
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-3">
          <div class="h-2 rounded-full transition-all" :class="{
            'bg-green-500': review.ai_risk_score >= 80,
            'bg-yellow-500': review.ai_risk_score >= 50 && review.ai_risk_score < 80,
            'bg-red-500': review.ai_risk_score < 50,
          }" :style="{ width: review.ai_risk_score + '%' }" />
        </div>
      </div>
      <div class="space-y-2">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">问题清单 ({{ getAllIssues().length }})</h3>
        <div v-for="issue in getAllIssues()" :key="issue.rule_id"
          class="p-2 rounded-lg text-sm cursor-pointer border transition-colors break-words"
          :class="{
            'border-red-200 bg-red-50 dark:bg-red-900/20': issue.match_type === '绝对化用语' || issue.match_type === '涉医用语',
            'border-orange-200 bg-orange-50 dark:bg-orange-900/20': issue.match_type === '效果保证' || issue.match_type === '功效宣称',
            'border-sky-200 bg-sky-50 dark:bg-sky-900/20': issue.match_type === '需证明材料',
            'border-gray-200 bg-gray-50 dark:bg-gray-800': !['绝对化用语', '涉医用语', '效果保证', '功效宣称', '需证明材料'].includes(issue.match_type),
          }">
          <span class="text-xs px-1.5 py-0.5 rounded mr-1.5"
            :class="{
              'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400': issue.match_type === '绝对化用语' || issue.match_type === '涉医用语',
              'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400': issue.match_type === '效果保证' || issue.match_type === '功效宣称',
              'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-400': issue.match_type === '需证明材料',
              'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300': !['绝对化用语', '涉医用语', '效果保证', '功效宣称', '需证明材料'].includes(issue.match_type),
            }">{{ issue.match_type }}</span>
          <span class="text-gray-700 dark:text-gray-300">{{ issue.rule_text }}</span>
        </div>
        <p v-if="!getAllIssues().length" class="text-sm text-gray-400">未发现问题</p>
      </div>
    </template>

    <template #center>
      <div class="card mb-4">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-semibold text-gray-800 dark:text-gray-200">{{ material.name }}</h3>
          <StatusBadge variant="info">第 {{ material.current_version }} 次提交</StatusBadge>
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ material.raw_text }}</p>
        <div class="flex gap-2 mt-2 text-xs text-gray-400">
          <span>{{ material.industry }}</span>
          <span>{{ material.platforms.join('、') }}</span>
        </div>
      </div>

      <div v-if="versions.length > 1" class="card">
        <button @click="showVersions = !showVersions" class="flex items-center justify-between w-full text-left">
          <h4 class="font-medium text-sm text-gray-700 dark:text-gray-300">历史版本 ({{ versions.length }})</h4>
          <span class="text-xs text-sky-600">{{ showVersions ? '收起' : '展开' }}</span>
        </button>
        <div v-if="showVersions" class="mt-3 space-y-2">
          <button v-for="v in versions" :key="v.review_id" type="button" @click="openHistory(v)"
            class="flex items-center justify-between text-sm py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
            :class="{ 'bg-sky-50 dark:bg-sky-900/20 -mx-2 px-2 rounded': v.version === review?.version }">
            <div>
              <span class="font-medium text-gray-700 dark:text-gray-300">{{ v.version_label }}</span>
              <span v-if="v.version === review?.version" class="text-xs text-sky-600 ml-2">当前</span>
            </div>
            <div class="flex gap-3 text-xs text-gray-500">
              <span>风险分: {{ v.risk_score }}</span>
              <span v-if="v.legal_decision" :class="{ 'text-green-600': v.legal_decision === 'approved', 'text-red-600': v.legal_decision === 'returned' }">
                {{ v.legal_decision === 'approved' ? '通过' : v.legal_decision === 'returned' ? '退回' : v.legal_decision }}
              </span>
              <span>{{ v.legal_review_label }}</span>
            </div>
          </button>
        </div>
      </div>
    </template>

    <template #right>
      <div class="space-y-4">
        <EngineReport :result="review.ai_result" />
      </div>

      <!-- Brand memory card -->
      <BrandMemoryCard
        v-if="material.brand_id"
        :profile="brandProfile"
        :loading="brandProfileLoading"
        class="mt-6"
      />

      <div v-if="store.isLegal && review.legal_decision === null" class="card mt-6">
        <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">法务审核决定</h3>
        <div class="space-y-3">
          <div class="flex gap-3">
            <label class="flex items-center gap-1 text-sm"><input type="radio" v-model="decision" value="approved" /> 通过</label>
            <label class="flex items-center gap-1 text-sm"><input type="radio" v-model="decision" value="returned" /> 退回</label>
            <label class="flex items-center gap-1 text-sm"><input type="radio" v-model="decision" value="conditional" /> 有条件通过</label>
          </div>
          <div v-if="decision !== 'approved'">
            <label class="label">退回原因</label>
            <textarea v-model="returnReasons" class="input h-20" placeholder="请说明退回或条件..."></textarea>
          </div>
          <div>
            <label class="label">法务备注</label>
            <textarea v-model="notes" class="input h-20" placeholder="内部备注..."></textarea>
          </div>
          <p v-if="decisionError" class="text-sm text-red-500">{{ decisionError }}</p>
          <button @click="handleDecision" :disabled="submitting" class="btn-primary w-full">
            {{ submitting ? '提交中...' : '提交决定' }}
          </button>
        </div>
      </div>

      <div v-else-if="review.legal_decision" class="card mt-6">
        <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-2">审核结果</h3>
        <p :class="{ 'text-green-600': review.legal_decision === 'approved', 'text-red-600': review.legal_decision === 'returned', 'text-yellow-600': review.legal_decision === 'conditional' }" class="font-bold">
          {{ review.legal_decision === 'approved' ? '已通过' : review.legal_decision === 'returned' ? '已退回' : '有条件通过' }}
        </p>
        <p v-if="review.return_reasons" class="text-sm text-gray-600 dark:text-gray-300 mt-2">{{ review.return_reasons }}</p>
        <p v-if="review.legal_notes" class="text-sm text-gray-500 mt-1">备注: {{ review.legal_notes }}</p>
      </div>
    </template>
  </ReviewLayout>
  <div v-else class="flex items-center justify-center min-h-[60vh] text-gray-500">加载中...</div>
  <ReviewHistoryDrawer :open="Boolean(selectedVersion)" :version="selectedVersion" :review="selectedReview" @close="selectedVersion = null" />
</template>
