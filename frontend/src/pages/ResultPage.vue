<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import ReviewLayout from '@/layouts/ReviewLayout.vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
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
const pageError = ref('')
const networkWarning = ref('')
const selectedRule = ref<MatchedRule | null>(null)
const retrying = ref(false)
const pollStartedAt = ref(Date.now())
let pollTimer: ReturnType<typeof setTimeout> | null = null
let consecutivePollErrors = 0

const isProcessing = computed(() => review.value?.task_status === 'processing')
const isFailed = computed(() => review.value?.task_status === 'failed')
const longRunning = computed(() => isProcessing.value && Date.now() - pollStartedAt.value > 60_000)

function getAllIssues(): MatchedRule[] {
  if (!review.value || review.value.task_status !== 'completed') return []
  const result = review.value.ai_result
  return [
    ...(result.layer1?.matched_rules ?? []),
    ...(result.layer2?.matched_rules ?? []),
    ...(result.layer3?.matched_rules ?? []),
  ]
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function getHighlightedHtml(): string {
  if (!material.value) return ''
  let safeText = escapeHtml(material.value.raw_text)
  for (const issue of getAllIssues()) {
    if (!issue.rule_text) continue
    const safeRule = escapeHtml(issue.rule_text)
    const colorMap: Record<string, string> = {
      '绝对化用语': '#ef4444',
      '涉医用语': '#ef4444',
      high: '#ef4444',
      '效果保证': '#f97316',
      '功效宣称': '#f97316',
      medium: '#f97316',
      '需证明材料': '#0EA5E9',
    }
    const color = colorMap[issue.match_type] || '#6b7280'
    safeText = safeText.replace(
      safeRule,
      `<mark style="background:${color}20;border-bottom:2px solid ${color}" class="px-0.5 rounded">${safeRule}</mark>`,
    )
  }
  return safeText
}

async function loadReview() {
  try {
    const reviewId = route.params.id as string
    const response = await reviewsApi.get(reviewId)
    review.value = response.data
    consecutivePollErrors = 0
    networkWarning.value = ''

    if (!material.value || material.value.id !== response.data.material_id) {
      const materialResponse = await materialsApi.get(response.data.material_id)
      material.value = materialResponse.data
    }

    if (response.data.task_status === 'processing') {
      schedulePoll()
    }
  } catch (error: any) {
    if (review.value?.task_status === 'processing') {
      consecutivePollErrors += 1
      networkWarning.value = '暂时无法刷新审查状态，系统将自动重试。'
      if (consecutivePollErrors < 5) schedulePoll(4000)
      else pageError.value = '连续多次无法连接审查服务，请返回工作台后稍后再查看。'
    } else {
      pageError.value = error.response?.data?.detail || '无法加载审查结果'
    }
  } finally {
    loading.value = false
  }
}

function schedulePoll(delay = 2000) {
  if (pollTimer) clearTimeout(pollTimer)
  pollTimer = setTimeout(loadReview, delay)
}

async function retryReview() {
  if (!material.value) return
  retrying.value = true
  pageError.value = ''
  try {
    const response = await reviewsApi.aiReview(material.value.id)
    review.value = response.data
    pollStartedAt.value = Date.now()
    await router.replace(`/result/${response.data.id}`)
    schedulePoll(500)
  } catch (error: any) {
    pageError.value = error.response?.data?.detail || '重新发起审查失败'
  } finally {
    retrying.value = false
  }
}

onMounted(loadReview)
onUnmounted(() => {
  if (pollTimer) clearTimeout(pollTimer)
})
</script>

<template>
  <ReviewLayout v-if="!loading && material && review?.task_status === 'completed'">
    <template #left>
      <ScoreBox :score="review.ai_risk_score" />
      <IssueList :issues="getAllIssues()" @select="selectedRule = $event" />
      <div class="mt-6 space-y-2">
        <div class="rounded-lg bg-sky-50 px-3 py-2 text-xs text-sky-700">
          AI 审查已完成，物料已自动进入法务待审队列。
        </div>
        <button class="btn-outline w-full text-sm" @click="router.push('/')">返回工作台</button>
      </div>
    </template>
    <template #center>
      <SummaryPanel :result="review.ai_result" :material-name="material.name" />
      <div
        class="mt-4 p-4 bg-white rounded-lg border text-sm leading-relaxed whitespace-pre-wrap"
        v-html="getHighlightedHtml()"
      />
    </template>
    <template #right>
      <EngineReport :result="review.ai_result" />
    </template>
  </ReviewLayout>

  <DefaultLayout v-else>
    <div class="min-h-[calc(100vh-3.5rem)] flex items-center justify-center p-4">
      <div class="card w-full max-w-lg text-center">
        <template v-if="loading">
          <div class="w-10 h-10 border-3 border-sky-100 border-t-sky-500 rounded-full animate-spin mx-auto mb-4" />
          <h2 class="text-lg font-semibold text-gray-800">正在加载审查任务</h2>
        </template>

        <template v-else-if="isProcessing">
          <div class="w-12 h-12 bg-sky-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <div class="w-6 h-6 border-3 border-sky-200 border-t-sky-600 rounded-full animate-spin" />
          </div>
          <h2 class="text-lg font-semibold text-gray-800">AI 正在审查物料</h2>
          <p class="text-sm text-gray-500 mt-2">规则匹配、语义分析和证据检查正在后台进行。</p>
          <p v-if="longRunning" class="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2 mt-4">
            本次审查耗时较长，但任务仍在后台运行。你可以先返回工作台，稍后再次查看。
          </p>
          <p v-if="networkWarning" class="text-xs text-orange-600 mt-3">{{ networkWarning }}</p>
          <p v-if="pageError" class="text-xs text-red-500 mt-3">{{ pageError }}</p>
          <button class="btn-outline w-full mt-6" @click="router.push('/')">返回工作台</button>
        </template>

        <template v-else-if="isFailed">
          <div class="w-12 h-12 bg-red-50 text-red-500 rounded-full flex items-center justify-center mx-auto mb-4 text-xl">!</div>
          <h2 class="text-lg font-semibold text-gray-800">审查未能完成</h2>
          <p class="text-sm text-gray-500 mt-2">{{ review?.error_message || '审查服务暂时不可用，请稍后重试。' }}</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-6">
            <button class="btn-outline" @click="router.push('/')">返回工作台</button>
            <button class="btn-primary" :disabled="retrying" @click="retryReview">
              {{ retrying ? '正在重新提交...' : '重新审查' }}
            </button>
          </div>
        </template>

        <template v-else>
          <h2 class="text-lg font-semibold text-gray-800">无法显示审查结果</h2>
          <p class="text-sm text-red-500 mt-2">{{ pageError || '审查状态异常' }}</p>
          <button class="btn-outline w-full mt-6" @click="router.push('/')">返回工作台</button>
        </template>
      </div>
    </div>
  </DefaultLayout>
</template>
