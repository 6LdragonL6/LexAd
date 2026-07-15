<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import { useUserStore } from '@/stores/user'
import ReviewLayout from '@/layouts/ReviewLayout.vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BrandMemoryCard from '@/components/brand/BrandMemoryCard.vue'
import ReviewHistoryDrawer from '@/components/review/ReviewHistoryDrawer.vue'
import EngineReport from '@/components/review/EngineReport.vue'
import PublicOpinionReport from '@/components/review/PublicOpinionReport.vue'
import RiskApprovalDialog from '@/components/review/RiskApprovalDialog.vue'
import { brandsApi } from '@/api/brands'
import { useReturnNavigation } from '@/composables/useReturnNavigation'
import { confirmedRiskIssues, highestRiskLabel, requiresRiskApproval } from '@/utils/review'
import type { Material, Review, MatchedRule, BrandProfile, MaterialVersion } from '@/types'

const route = useRoute()
const store = useUserStore()
const { returnLabel, returnToSource } = useReturnNavigation()
const material = ref<Material | null>(null)
const review = ref<Review | null>(null)
const loading = ref(true)
const versions = ref<MaterialVersion[]>([])
const showVersions = ref(true)
const selectedVersion = ref<MaterialVersion | null>(null)
const selectedReview = ref<Review | null>(null)
const historyLoading = ref(false)
const historyError = ref('')
const decision = ref('approved')
const notes = ref('')
const returnReasons = ref('')
const submitting = ref(false)
const decisionError = ref('')
const brandProfile = ref<BrandProfile | null>(null)
const brandProfileLoading = ref(false)
const publicOpinionManuallyReviewed = ref(false)
const showRiskApproval = ref(false)
const pageError = ref('')

const publicOpinionPending = computed(() => ['pending', 'running'].includes(review.value?.public_opinion_module_status || ''))
const publicOpinionNeedsManualReview = computed(() => {
  const status = review.value?.public_opinion_module_status
  const result = review.value?.public_opinion_result || {}
  return !status
    || ['failed', 'unavailable'].includes(status)
    || !Object.keys(result).length
    || result.status === 'manual_review'
    || Boolean(result.requires_manual_review)
})
const canSubmitDecision = computed(() => !publicOpinionPending.value && (!publicOpinionNeedsManualReview.value || publicOpinionManuallyReviewed.value))

function getAllIssues(): MatchedRule[] {
  return confirmedRiskIssues(review.value?.ai_result)
}

const highestConfirmedRisk = computed(() => highestRiskLabel(getAllIssues()))

function riskLabel(issue: MatchedRule) {
  if (issue.risk_level_label) return issue.risk_level_label
  return ({ high: '高风险', medium: '中风险', low: '低风险', severe: '严重风险' } as Record<string, string>)[issue.risk_level || issue.match_type] || '已确认风险'
}

function riskTypeLabel(value?: string) {
  return ({ high: '高风险问题', medium: '中风险问题', low: '低风险问题', severe: '严重风险问题' } as Record<string, string>)[value || ''] || value || '合规风险'
}

onMounted(async () => {
  try {
    const reviewId = route.params.id as string
    const rRes = await reviewsApi.get(reviewId)
    review.value = rRes.data
    const mRes = await materialsApi.get(rRes.data.material_id)
    material.value = mRes.data
  } catch (error: any) {
    pageError.value = error.response?.data?.detail || '无法加载审核详情'
  } finally {
    loading.value = false
  }

  if (!review.value || !material.value) return
  try {
    const vRes = await materialsApi.versions(review.value.material_id)
    versions.value = vRes.data.versions || []
  } catch {
    versions.value = []
  }

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
  if (requiresRiskApproval(decision.value, review.value?.ai_result)) {
    decisionError.value = ''
    showRiskApproval.value = true
    return
  }
  await submitDecision()
}

async function submitDecision() {
  if (!review.value) return
  submitting.value = true
  decisionError.value = ''
  try {
    await reviewsApi.submitDecision(review.value.id, {
      decision: decision.value,
      notes: notes.value,
      return_reasons: returnReasons.value,
      public_opinion_manually_reviewed: publicOpinionManuallyReviewed.value,
    })
    showRiskApproval.value = false
    await returnToSource(true)
  } catch (error: any) {
    decisionError.value = error.response?.data?.detail || '法务决定提交失败'
  } finally {
    submitting.value = false
  }
}

function cancelRiskApproval() {
  if (submitting.value) return
  showRiskApproval.value = false
  decisionError.value = ''
}

async function openHistory(version: MaterialVersion) {
  selectedVersion.value = version
  selectedReview.value = null
  historyError.value = ''
  historyLoading.value = true
  try {
    selectedReview.value = (await reviewsApi.get(version.review_id)).data
  } catch (error: any) {
    historyError.value = error.response?.data?.detail || '无法加载该历史审核报告'
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
          'text-green-500': review.legal_compliance_score >= 80,
          'text-yellow-500': review.legal_compliance_score >= 60 && review.legal_compliance_score < 80,
          'text-red-500': review.legal_compliance_score < 60,
        }">{{ review.legal_compliance_score }}</div>
        <p class="text-sm text-gray-400 mt-1">法规合规分 / 100 · 越高越合规</p>
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-3">
          <div class="h-2 rounded-full transition-all" :class="{
            'bg-green-500': review.legal_compliance_score >= 80,
            'bg-yellow-500': review.legal_compliance_score >= 60 && review.legal_compliance_score < 80,
            'bg-red-500': review.legal_compliance_score < 60,
          }" :style="{ width: review.legal_compliance_score + '%' }" />
        </div>
      </div>
      <div class="space-y-2">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">问题清单 ({{ getAllIssues().length }})</h3>
        <div v-for="issue in getAllIssues()" :key="issue.rule_id"
          class="p-2 rounded-lg text-sm cursor-pointer border transition-colors break-words"
          :class="{
            'border-red-200 bg-red-50 dark:bg-red-900/20': issue.risk_level === 'high' || issue.match_type === 'high',
            'border-orange-200 bg-orange-50 dark:bg-orange-900/20': issue.risk_level === 'medium' || issue.match_type === 'medium',
            'border-sky-200 bg-sky-50 dark:bg-sky-900/20': issue.risk_level === 'low' || issue.match_type === 'low',
          }">
          <span class="text-xs px-1.5 py-0.5 rounded mr-1.5"
            :class="{
              'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400': issue.risk_level === 'high' || issue.match_type === 'high',
              'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400': issue.risk_level === 'medium' || issue.match_type === 'medium',
              'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-400': issue.risk_level === 'low' || issue.match_type === 'low',
            }">{{ riskLabel(issue) }}</span>
          <span class="text-gray-700 dark:text-gray-300">{{ riskTypeLabel(issue.match_type) }}：{{ issue.evidence_quote || issue.rule_text }}</span>
        </div>
        <p v-if="!getAllIssues().length" class="text-sm text-gray-400">未发现问题</p>
      </div>
    </template>

    <template #center>
      <div class="flex items-center justify-between gap-3 mb-4">
        <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">法务审核详情</h2>
        <button type="button" class="btn-outline text-sm" @click="returnToSource()">{{ returnLabel }}</button>
      </div>
      <div class="card mb-4">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-semibold text-gray-800 dark:text-gray-200">{{ review.submission?.name || '历史快照缺失' }}</h3>
          <StatusBadge variant="info">第 {{ review.version }} 次提交</StatusBadge>
        </div>
        <p v-if="review.submission" class="text-sm leading-7 text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ review.submission.raw_text }}</p>
        <p v-else class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">该审核未保存完整提交快照，系统不会使用当前物料内容代替历史版本。</p>
        <div class="flex gap-2 mt-2 text-xs text-gray-400">
          <span>{{ review.submission?.industry || '-' }}</span>
          <span>{{ review.submission?.platforms.join('、') || '未指定平台' }}</span>
        </div>
      </div>

      <div class="mb-4 text-center">
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-sky-500 dark:text-sky-300">Review engine</p>
        <h2 class="mt-1 text-lg font-semibold text-gray-800 dark:text-gray-100">审查引擎·执行报告</h2>
      </div>
      <div class="card mb-4"><EngineReport :result="review.ai_result" /></div>
      <PublicOpinionReport :review="review" />
    </template>

    <template #right>
      <div v-if="versions.length > 1" class="card mb-4">
        <button @click="showVersions = !showVersions" class="flex items-center justify-between w-full text-left">
          <h4 class="font-medium text-sm text-gray-700 dark:text-gray-200">历史版本 ({{ versions.length }})</h4>
          <span class="text-xs text-sky-600 dark:text-sky-400">{{ showVersions ? '收起' : '展开' }}</span>
        </button>
        <div v-if="showVersions" class="mt-3 space-y-1">
          <button v-for="v in versions" :key="v.review_id" type="button" @click="openHistory(v)"
            class="w-full rounded-lg px-2 py-2 text-left text-sm transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
            :class="{ 'bg-sky-50 dark:bg-sky-950/30': v.version === review?.version }">
            <div class="flex items-center justify-between gap-2">
              <span class="font-medium text-gray-700 dark:text-gray-200">{{ v.version_label }}</span>
              <span v-if="v.version === review?.version" class="text-xs text-sky-600 dark:text-sky-400">当前</span>
            </div>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ v.legal_review_label }} · 合规分 {{ v.legal_compliance_score }}</p>
          </button>
        </div>
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
          <div v-if="publicOpinionPending" class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
            舆情审查仍在处理，完成前不能提交法务决定。
          </div>
          <label v-if="publicOpinionNeedsManualReview" class="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
            <input v-model="publicOpinionManuallyReviewed" type="checkbox" class="mt-0.5" />
            <span>舆情引擎不可用，我已完成人工舆情复核并愿意提交决定。</span>
          </label>
          <p v-if="decisionError" class="text-sm text-red-500">{{ decisionError }}</p>
          <button @click="handleDecision" :disabled="submitting || !canSubmitDecision" class="btn-primary w-full">
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
  <DefaultLayout v-else>
    <div class="page-container max-w-lg min-h-[60vh] flex items-center justify-center">
      <div class="card w-full text-center">
        <p :class="pageError ? 'text-red-500' : 'text-gray-500'">{{ pageError || '加载中...' }}</p>
        <button type="button" class="btn-outline w-full mt-5" @click="returnToSource()">{{ returnLabel }}</button>
      </div>
    </div>
  </DefaultLayout>
  <ReviewHistoryDrawer
    :open="Boolean(selectedVersion)"
    :version="selectedVersion"
    :review="selectedReview"
    :loading="historyLoading"
    :error="historyError"
    @close="selectedVersion = null"
  />
  <RiskApprovalDialog
    :open="showRiskApproval"
    :issue-count="getAllIssues().length"
    :highest-risk="highestConfirmedRisk"
    :submitting="submitting"
    :error="decisionError"
    @cancel="cancelRiskApproval"
    @confirm="submitDecision"
  />
</template>
