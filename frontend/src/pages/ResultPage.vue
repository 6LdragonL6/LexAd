<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BrandMemoryCard from '@/components/brand/BrandMemoryCard.vue'
import ReviewHistoryDrawer from '@/components/review/ReviewHistoryDrawer.vue'
import HistoricalConsequencePanel from '@/components/review/HistoricalConsequencePanel.vue'
import { brandsApi } from '@/api/brands'
import type { Material, MatchedRule, Review, BrandProfile, MaterialVersion } from '@/types'

const route = useRoute()
const router = useRouter()

const material = ref<Material | null>(null)
const review = ref<Review | null>(null)
const loading = ref(true)
const pageError = ref('')
const networkWarning = ref('')
const retrying = ref(false)
const pollStartedAt = ref(Date.now())
let pollTimer: ReturnType<typeof setTimeout> | null = null
let consecutivePollErrors = 0

const brandProfile = ref<BrandProfile | null>(null)
const brandProfileLoading = ref(false)
const versions = ref<MaterialVersion[]>([])
const selectedVersion = ref<MaterialVersion | null>(null)
const selectedReview = ref<Review | null>(null)
const historyLoading = ref(false)
const historyError = ref('')

const isProcessing = computed(() => review.value?.task_status === 'processing')
const isFailed = computed(() => review.value?.task_status === 'failed')
const longRunning = computed(() => isProcessing.value && Date.now() - pollStartedAt.value > 60_000)

const legalStatus = computed(() => review.value?.legal_module_status || (review.value?.task_status === 'completed' ? 'succeeded' : 'pending'))
const publicOpinionStatus = computed(() => review.value?.public_opinion_module_status || 'pending')
const publicOpinion = computed(() => review.value?.public_opinion_result || {})

const legalIssues = computed<MatchedRule[]>(() => {
  const result = review.value?.ai_result
  if (!result) return []
  return [
    ...(result.layer1?.matched_rules ?? []),
    ...(result.layer2?.matched_rules ?? []),
    ...(result.layer3?.matched_rules ?? []),
    ...(result.layer4?.matched_rules ?? []),
  ]
})

const publicOpinionRiskLabel = computed(() => {
  const level = publicOpinion.value.risk_level || 'unavailable'
  const map: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
    severe: '严重',
    uncertain: '不确定',
    unavailable: '资料库待补充',
  }
  return map[level] || level
})

const publicOpinionRiskClass = computed(() => {
  const level = publicOpinion.value.risk_level
  if (level === 'severe' || level === 'high') return 'text-red-600 bg-red-50 border-red-200'
  if (level === 'medium') return 'text-orange-600 bg-orange-50 border-orange-200'
  if (level === 'low') return 'text-green-700 bg-green-50 border-green-200'
  return 'text-gray-600 bg-gray-50 border-gray-200'
})

const publicOpinionSourceLabel = computed(() => {
  const map: Record<string, string> = { local: '本地证据', ai: 'AI 语义', hybrid: '本地 + AI' }
  return map[publicOpinion.value.assessment_source] || '证据不足'
})

function statusText(status?: string | null) {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '分析中',
    succeeded: '已完成',
    failed: '失败',
    unavailable: '不可用',
    processing: '处理中',
    completed: '已完成',
  }
  return map[status || ''] || status || '-'
}

function statusClass(status?: string | null) {
  if (status === 'succeeded' || status === 'completed') return 'bg-green-100 text-green-700'
  if (status === 'failed') return 'bg-red-100 text-red-600'
  if (status === 'unavailable') return 'bg-gray-100 text-gray-600'
  return 'bg-yellow-100 text-yellow-700'
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function highlightedHtml(): string {
  if (!material.value) return ''
  const fragments = new Map<string, string>()
  for (const issue of legalIssues.value) {
    const color = issue.rule_id?.startsWith('L4-') ? '#0EA5E9' : '#f97316'
    const candidates = issue.matched_text
      ? issue.matched_text.split(/[,，、；;]/)
      : [issue.rule_text]
    for (const candidate of candidates) {
      const fragment = candidate.trim()
      if (fragment.length >= 2 && material.value.raw_text.includes(fragment)) {
        fragments.set(fragment, color)
      }
    }
  }
  if (!fragments.size) return escapeHtml(material.value.raw_text)

  const ordered = [...fragments.keys()].sort((left, right) => right.length - left.length)
  const pattern = new RegExp(ordered.map(escapeRegExp).join('|'), 'gu')
  let output = ''
  let lastIndex = 0
  for (const match of material.value.raw_text.matchAll(pattern)) {
    const index = match.index ?? 0
    const text = match[0]
    const color = fragments.get(text) || '#f97316'
    output += escapeHtml(material.value.raw_text.slice(lastIndex, index))
    output += `<mark style="background:${color}20;border-bottom:2px solid ${color}" class="px-0.5 rounded">${escapeHtml(text)}</mark>`
    lastIndex = index + text.length
  }
  return output + escapeHtml(material.value.raw_text.slice(lastIndex))
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
      const versionsResponse = await materialsApi.versions(response.data.material_id)
      versions.value = versionsResponse.data.versions || []
    }

    if (response.data.task_status === 'processing') schedulePoll()
    if (material.value?.brand_id) loadBrandProfile(material.value.brand_id)
  } catch (error: any) {
    if (review.value?.task_status === 'processing') {
      consecutivePollErrors += 1
      networkWarning.value = '暂时无法刷新审查状态，系统会自动重试。'
      if (consecutivePollErrors < 5) schedulePoll(4000)
      else pageError.value = '连续多次无法连接审查服务，请稍后再查看。'
    } else {
      pageError.value = error.response?.data?.detail || '无法加载审查结果'
    }
  } finally {
    loading.value = false
  }
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

function schedulePoll(delay = 2000) {
  if (pollTimer) clearTimeout(pollTimer)
  pollTimer = setTimeout(loadReview, delay)
}

async function loadBrandProfile(brandId: string) {
  brandProfileLoading.value = true
  try {
    const res = await brandsApi.profile(brandId)
    brandProfile.value = res.data
  } catch {
    brandProfile.value = null
  } finally {
    brandProfileLoading.value = false
  }
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
  <DefaultLayout>
    <div v-if="!loading && material && review?.task_status === 'completed'" class="page-container max-w-7xl">
      <div class="responsive-toolbar mb-6">
        <div class="min-w-0">
          <div class="flex items-center gap-3 mb-2 flex-wrap">
            <h2 class="page-heading !mb-0">审查结果</h2>
            <StatusBadge :variant="review.ai_risk_score >= 80 ? 'success' : review.ai_risk_score >= 60 ? 'warning' : 'danger'">
              {{ review.ai_risk_score >= 80 ? '低风险' : review.ai_risk_score >= 60 ? '中风险' : '高风险' }}
            </StatusBadge>
            <span class="text-sm text-gray-400">{{ formatDate(review.completed_at) }}</span>
          </div>
          <p class="text-sm text-gray-500 break-words">{{ material.name }} · {{ material.industry }} · {{ material.platforms.join('、') || '未指定平台' }}</p>
        </div>
        <button class="btn-outline text-sm shrink-0" @click="router.push('/')">返回工作台</button>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_340px] gap-6">
        <main class="space-y-5 min-w-0">
          <section class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="card border-l-4 border-l-sky-500">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-sm text-gray-400">法律合规风险</p>
                  <p class="text-4xl font-bold text-gray-800 dark:text-gray-200 mt-2">{{ review.ai_risk_score }}</p>
                  <p class="text-xs text-gray-400 mt-1">/100，分数越高风险越低</p>
                </div>
                <StatusBadge :variant="legalStatus === 'succeeded' ? 'success' : legalStatus === 'failed' ? 'danger' : 'warning'">
                  {{ statusText(legalStatus) }}
                </StatusBadge>
              </div>
              <p v-if="review.legal_module_error" class="mt-3 text-sm text-red-500">{{ review.legal_module_error }}</p>
              <div class="mt-4 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ review.ai_result?.summary }}</div>
            </div>

            <div class="card border-l-4 border-l-purple-500">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-sm text-gray-400">舆情风险</p>
                  <p class="text-3xl font-bold mt-2" :class="publicOpinionRiskLabel === '低' ? 'text-green-600' : publicOpinionRiskLabel === '高' || publicOpinionRiskLabel === '严重' ? 'text-red-600' : 'text-amber-600'">
                    {{ publicOpinionRiskLabel }}
                  </p>
                  <p class="text-xs text-gray-400 mt-1">
                    {{ publicOpinion.risk_score ?? '-' }}/100 · {{ publicOpinionSourceLabel }} · 不计入法律合规分
                  </p>
                </div>
                <StatusBadge :variant="publicOpinionStatus === 'succeeded' ? 'success' : publicOpinionStatus === 'unavailable' ? 'gray' : publicOpinionStatus === 'failed' ? 'danger' : 'warning'">
                  {{ statusText(publicOpinionStatus) }}
                </StatusBadge>
              </div>
              <div class="mt-4 rounded-lg border px-3 py-2 text-sm" :class="publicOpinionRiskClass">
                {{ publicOpinion.explanation || publicOpinion.message || '暂无舆情分析说明' }}
              </div>
              <p v-if="review.public_opinion_module_error && publicOpinionStatus !== 'unavailable'" class="mt-3 text-sm text-red-500">
                {{ review.public_opinion_module_error }}
              </p>
            </div>
          </section>

          <section class="card">
            <div class="flex items-center justify-between gap-3 mb-4">
              <h3 class="font-semibold text-gray-800 dark:text-gray-200">物料内容与命中标记</h3>
              <span class="text-xs text-gray-400">{{ legalIssues.length }} 项命中</span>
            </div>
            <div class="rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 text-sm leading-7 whitespace-pre-wrap" v-html="highlightedHtml()" />
          </section>

          <section class="card">
            <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-4">法律与平台规则依据</h3>
            <div v-if="legalIssues.length" class="space-y-3">
              <div v-for="issue in legalIssues" :key="issue.rule_id" class="flex gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div class="w-1.5 rounded flex-shrink-0" :class="issue.rule_id?.startsWith('L4-') ? 'bg-sky-500' : 'bg-orange-500'"></div>
                <div class="flex-1">
                  <div class="flex justify-between items-center mb-1">
                    <span class="font-semibold text-sm text-gray-800 dark:text-gray-200">{{ issue.match_type }}</span>
                    <StatusBadge :variant="issue.rule_id?.startsWith('L4-') ? 'info' : 'danger'">规则命中</StatusBadge>
                  </div>
                  <p class="text-sm text-gray-700 dark:text-gray-300">{{ issue.rule_text }}</p>
                  <p class="text-xs text-gray-400 mt-1">依据：{{ issue.source_law || '未提供' }}</p>
                </div>
              </div>
            </div>
            <p v-else class="text-sm text-gray-400">未命中明确法律或平台规则。</p>
          </section>

          <section class="card">
            <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-4">舆情风险详情</h3>
            <div v-if="publicOpinion.requires_manual_review" class="rounded-xl bg-orange-50 text-orange-700 border border-orange-200 p-4 text-sm mb-4">
              <p class="font-semibold">建议人工复核</p>
              <p class="mt-1">{{ publicOpinion.disagreement_reason || '当前有效证据不足，不能直接作为低风险结论。' }}</p>
            </div>
            <div v-if="publicOpinion.model_available === false" class="rounded-xl bg-yellow-50 text-yellow-700 p-3 text-sm mb-4">
              AI 语义判断暂不可用，当前结果来自本地规则与真实案例。
            </div>
            <div v-if="publicOpinion.knowledge_base_available === false" class="rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-300 p-3 text-sm mb-4">
              当前没有可用本地舆情案例；系统仍会执行 AI 开放式语义判断。
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                <p class="text-xs text-gray-400">风险议题</p>
                <p class="text-sm text-gray-700 dark:text-gray-300 mt-2">{{ publicOpinion.risk_topics?.join('、') || '暂无' }}</p>
              </div>
              <div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                <p class="text-xs text-gray-400">受影响群体</p>
                <p class="text-sm text-gray-700 dark:text-gray-300 mt-2">{{ publicOpinion.affected_groups?.join('、') || '暂无' }}</p>
              </div>
              <div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                <p class="text-xs text-gray-400">传播诱因</p>
                <p class="text-sm text-gray-700 dark:text-gray-300 mt-2">{{ publicOpinion.propagation_drivers?.join('、') || '暂无' }}</p>
              </div>
              <div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                <p class="text-xs text-gray-400">置信度</p>
                <p class="text-sm text-gray-700 dark:text-gray-300 mt-2">{{ publicOpinion.confidence ?? '-' }}<span v-if="publicOpinion.confidence !== undefined">%</span></p>
              </div>
            </div>
            <div v-if="publicOpinion.evidence_quotes?.length" class="mt-5">
              <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">判断证据</h4>
              <div class="flex flex-wrap gap-2">
                <span v-for="quote in publicOpinion.evidence_quotes" :key="quote" class="rounded-lg bg-purple-50 dark:bg-purple-950/30 text-purple-700 dark:text-purple-300 px-3 py-1.5 text-sm">“{{ quote }}”</span>
              </div>
            </div>
            <div v-if="publicOpinion.similar_events?.length" class="mt-5">
              <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">相似舆情事件</h4>
              <div class="space-y-3">
                <div v-for="event in publicOpinion.similar_events" :key="event.event_id" class="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <span class="font-medium text-gray-800 dark:text-gray-200">{{ event.title }}</span>
                    <span class="text-xs text-gray-400">匹配分 {{ event.similarity }} · {{ event.verification_status || '待核验' }}</span>
                  </div>
                  <p v-if="event.matched_text" class="mt-2 text-xs text-purple-600">匹配依据：{{ event.matched_text }}</p>
                  <HistoricalConsequencePanel :value="event.historical_consequence" />
                </div>
              </div>
            </div>
            <div v-if="publicOpinion.suggestions?.length" class="mt-5">
              <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">舆情修改建议</h4>
              <ul class="space-y-2 text-sm text-gray-600 dark:text-gray-300">
                <li v-for="suggestion in publicOpinion.suggestions" :key="suggestion" class="flex gap-2"><span class="text-purple-500">•</span><span>{{ suggestion }}</span></li>
              </ul>
            </div>
          </section>

          <!-- Brand profile (if associated) -->
          <div v-if="material.brand_id" class="card">
            <BrandMemoryCard
              :profile="brandProfile"
              :loading="brandProfileLoading"
            />
          </div>
        </main>

        <aside class="space-y-4">
          <div class="card">
            <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">审核信息</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between"><span class="text-gray-500">版本</span><span class="font-medium">{{ review.version }} 次提交</span></div>
              <div class="flex justify-between"><span class="text-gray-500">完成时间</span><span class="font-medium">{{ formatDate(review.completed_at) }}</span></div>
              <div v-if="review.public_opinion_library_version_id" class="flex justify-between">
                <span class="text-gray-500">舆情资料库</span><span class="font-medium text-xs">{{ review.public_opinion_library_version_id }}</span>
              </div>
              <div v-if="review.ai_result?.platform_version_labels && Object.keys(review.ai_result.platform_version_labels).length" class="border-t border-gray-100 dark:border-gray-700 pt-2 mt-2">
                <p class="text-xs text-gray-400 mb-2">平台规则版本</p>
                <p v-for="(label, vid) in review.ai_result.platform_version_labels" :key="vid" class="text-sm text-gray-700 dark:text-gray-300">{{ label }}</p>
              </div>
            </div>
          </div>

          <div v-if="versions.length > 1" class="card">
            <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">历史版本</h3>
            <button v-for="version in versions" :key="version.review_id" type="button" class="w-full flex items-center justify-between py-2 text-left border-b border-gray-100 dark:border-gray-700 last:border-0" @click="openHistory(version)">
              <span class="text-sm font-medium">{{ version.version_label }}<span v-if="version.version === review.version" class="ml-2 text-xs text-sky-600">当前</span></span>
              <span class="text-xs text-gray-400">{{ version.legal_review_label }}</span>
            </button>
          </div>

          <div class="card">
            <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">平台状态</h3>
            <div v-if="review.ai_result?.unavailable_platforms?.length" class="space-y-2">
              <div v-for="p in review.ai_result.unavailable_platforms" :key="p" class="rounded-lg bg-yellow-50 text-yellow-700 p-3 text-sm">
                {{ p }}：暂无生效规则
              </div>
            </div>
            <div v-else class="flex flex-wrap gap-2">
              <span v-for="p in material.platforms" :key="p" class="badge badge-success">{{ p }} &#x2713;</span>
            </div>
          </div>

          <div class="card">
            <h3 class="font-semibold text-gray-800 dark:text-gray-200 mb-3">下一步</h3>
            <div class="text-sm text-gray-600 dark:text-gray-300 space-y-2">
              <template v-if="review.ai_result?.suggestions?.length">
                <div v-for="(s, i) in review.ai_result.suggestions.slice(0, 3)" :key="i" class="flex gap-3">
                  <div class="w-6 h-6 rounded-full bg-sky-500 text-white flex items-center justify-center text-xs font-semibold flex-shrink-0">{{ i + 1 }}</div>
                  <p>{{ s }}</p>
                </div>
              </template>
              <p v-else>结果已进入法务待审队列，请关注审核通知。</p>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <div v-else class="min-h-[calc(100vh-3.5rem)] flex items-center justify-center p-4">
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
          <p class="text-sm text-gray-500 mt-2">法律/平台规则和舆情风险分析正在后台执行。</p>
          <p v-if="longRunning" class="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2 mt-4">
            本次审查耗时较长，但任务仍在后台运行。可以先返回工作台，稍后再查看。
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
              {{ retrying ? '正在重新提交…' : '重新审查' }}
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
  <ReviewHistoryDrawer
    :open="Boolean(selectedVersion)"
    :version="selectedVersion"
    :review="selectedReview"
    :loading="historyLoading"
    :error="historyError"
    @close="selectedVersion = null"
  />
</template>
