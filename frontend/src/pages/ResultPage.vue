<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { materialsApi } from '@/api/materials'
import { reviewsApi } from '@/api/reviews'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import type { Material, MatchedRule, Review } from '@/types'

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

function highlightedHtml(): string {
  if (!material.value) return ''
  let safeText = escapeHtml(material.value.raw_text)
  for (const issue of legalIssues.value) {
    if (!issue.rule_text) continue
    const safeRule = escapeHtml(issue.rule_text)
    const color = issue.rule_id?.startsWith('L4-') ? '#0EA5E9' : '#f97316'
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

    if (response.data.task_status === 'processing') schedulePoll()
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
  <DefaultLayout>
    <div v-if="!loading && material && review?.task_status === 'completed'" class="max-w-7xl mx-auto p-4 lg:p-8">
      <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3 mb-6">
        <div>
          <h2 class="page-heading !mb-1">风险审查结果</h2>
          <p class="text-sm text-gray-500">{{ material.name }} · {{ material.industry }} · {{ material.platforms.join('、') || '未指定平台' }}</p>
        </div>
        <button class="btn-outline text-sm" @click="router.push('/')">返回工作台</button>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-6">
        <main class="space-y-6 min-w-0">
          <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div class="card border-l-4 border-l-sky-500">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-sm text-gray-400">法律合规风险</p>
                  <p class="text-4xl font-bold text-gray-800 mt-2">{{ review.ai_risk_score }}</p>
                  <p class="text-xs text-gray-400 mt-1">分数越高，合规风险越低</p>
                </div>
                <span class="px-2 py-0.5 rounded-full text-xs" :class="statusClass(legalStatus)">
                  {{ statusText(legalStatus) }}
                </span>
              </div>
              <p v-if="review.legal_module_error" class="mt-3 text-sm text-red-500">{{ review.legal_module_error }}</p>
              <div class="mt-4 text-sm text-gray-600 whitespace-pre-wrap">{{ review.ai_result?.summary }}</div>
            </div>

            <div class="card border-l-4 border-l-purple-500">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-sm text-gray-400">舆情风险</p>
                  <p class="text-3xl font-bold mt-2" :class="publicOpinionRiskClass.split(' ')[0]">{{ publicOpinionRiskLabel }}</p>
                  <p class="text-xs text-gray-400 mt-1">不计入法律合规分，单独提示品牌风险</p>
                </div>
                <span class="px-2 py-0.5 rounded-full text-xs" :class="statusClass(publicOpinionStatus)">
                  {{ statusText(publicOpinionStatus) }}
                </span>
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
              <h3 class="font-semibold text-gray-800">物料内容与命中标记</h3>
              <span class="text-xs text-gray-400">{{ legalIssues.length }} 项法律/平台命中</span>
            </div>
            <div class="rounded-xl bg-gray-50 border border-gray-100 p-4 text-sm leading-7 whitespace-pre-wrap" v-html="highlightedHtml()" />
          </section>

          <section class="card">
            <h3 class="font-semibold text-gray-800 mb-4">法律与平台规则依据</h3>
            <div v-if="legalIssues.length" class="space-y-3">
              <div v-for="issue in legalIssues" :key="issue.rule_id" class="rounded-xl border border-gray-200 p-4">
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <span class="font-medium text-gray-800">{{ issue.match_type }}</span>
                  <span class="text-xs text-gray-400">{{ issue.rule_id }}</span>
                </div>
                <p class="text-sm text-gray-700 mt-2">{{ issue.rule_text }}</p>
                <p class="text-xs text-gray-400 mt-2">依据：{{ issue.source_law || '未提供' }}</p>
              </div>
            </div>
            <p v-else class="text-sm text-gray-400">未命中明确法律或平台规则。</p>
          </section>

          <section class="card">
            <h3 class="font-semibold text-gray-800 mb-4">舆情风险详情</h3>
            <div v-if="publicOpinion.status === 'knowledge_base_empty'" class="rounded-xl bg-yellow-50 text-yellow-700 p-4 text-sm">
              {{ publicOpinion.message }}。这不是低风险结论，只表示资料库还不能支撑案例化判断。
            </div>
            <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div class="rounded-xl border border-gray-200 p-4">
                <p class="text-xs text-gray-400">风险议题</p>
                <p class="text-sm text-gray-700 mt-2">{{ publicOpinion.risk_topics?.join('、') || '暂无' }}</p>
              </div>
              <div class="rounded-xl border border-gray-200 p-4">
                <p class="text-xs text-gray-400">受影响群体</p>
                <p class="text-sm text-gray-700 mt-2">{{ publicOpinion.affected_groups?.join('、') || '暂无' }}</p>
              </div>
              <div class="rounded-xl border border-gray-200 p-4">
                <p class="text-xs text-gray-400">传播诱因</p>
                <p class="text-sm text-gray-700 mt-2">{{ publicOpinion.propagation_drivers?.join('、') || '暂无' }}</p>
              </div>
              <div class="rounded-xl border border-gray-200 p-4">
                <p class="text-xs text-gray-400">置信度</p>
                <p class="text-sm text-gray-700 mt-2">{{ publicOpinion.confidence ?? '-' }}</p>
              </div>
            </div>

            <div class="mt-5">
              <h4 class="text-sm font-semibold text-gray-700 mb-3">相似舆情事件</h4>
              <div v-if="publicOpinion.similar_events?.length" class="space-y-3">
                <div v-for="event in publicOpinion.similar_events" :key="event.event_id" class="rounded-xl border border-gray-200 p-4">
                  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <span class="font-medium text-gray-800">{{ event.title }}</span>
                    <span class="text-xs text-gray-400">相似度 {{ event.similarity }}</span>
                  </div>
                  <pre class="mt-2 text-xs text-gray-500 whitespace-pre-wrap">{{ JSON.stringify(event.historical_consequence || {}, null, 2) }}</pre>
                </div>
              </div>
              <p v-else class="text-sm text-gray-400">暂无相似事件。</p>
            </div>

            <div v-if="publicOpinion.suggestions?.length" class="mt-5 rounded-xl bg-purple-50 text-purple-700 p-4">
              <h4 class="text-sm font-semibold mb-2">建议</h4>
              <ul class="list-disc pl-5 text-sm space-y-1">
                <li v-for="suggestion in publicOpinion.suggestions" :key="suggestion">{{ suggestion }}</li>
              </ul>
            </div>
          </section>
        </main>

        <aside class="space-y-4">
          <div class="card">
            <h3 class="font-semibold text-gray-800 mb-3">资料版本快照</h3>
            <div class="space-y-3 text-sm">
              <div>
                <p class="text-xs text-gray-400">平台规则版本</p>
                <p class="text-gray-700 break-all">{{ review.platform_rule_version_ids?.join(', ') || '未命中或待补充' }}</p>
              </div>
              <div>
                <p class="text-xs text-gray-400">舆情资料库版本</p>
                <p class="text-gray-700 break-all">{{ review.public_opinion_library_version_id || '未使用' }}</p>
              </div>
              <div>
                <p class="text-xs text-gray-400">法律模块完成时间</p>
                <p class="text-gray-700">{{ formatDate(review.legal_module_completed_at) }}</p>
              </div>
              <div>
                <p class="text-xs text-gray-400">舆情模块完成时间</p>
                <p class="text-gray-700">{{ formatDate(review.public_opinion_module_completed_at) }}</p>
              </div>
            </div>
          </div>

          <div class="card">
            <h3 class="font-semibold text-gray-800 mb-3">平台规则状态</h3>
            <div v-if="review.ai_result?.unavailable_platforms?.length" class="rounded-lg bg-yellow-50 text-yellow-700 p-3 text-sm">
              以下平台暂无生效规则：{{ review.ai_result.unavailable_platforms.join('、') }}。这不是通过结论，需要管理员补充平台规则。
            </div>
            <p v-else class="text-sm text-gray-600">本次审核已固定可用平台规则版本。</p>
          </div>

          <div class="card">
            <h3 class="font-semibold text-gray-800 mb-3">下一步</h3>
            <p v-if="publicOpinion.risk_level === 'high' || publicOpinion.risk_level === 'severe'" class="text-sm text-red-600">
              法律低风险不代表可以直接发布。舆情风险较高，建议暂停发布并由品牌负责人复核。
            </p>
            <p v-else class="text-sm text-gray-600">
              结果已进入法务待审流程。请结合双风险轴和人工判断决定是否发布。
            </p>
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
</template>
