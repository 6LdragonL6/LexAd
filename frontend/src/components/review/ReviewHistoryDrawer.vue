<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { LayerResult, MaterialVersion, Review } from '@/types'

const props = defineProps<{
  open: boolean
  version: MaterialVersion | null
  review: Review | null
  loading?: boolean
  error?: string
}>()

const emit = defineEmits<{ close: [] }>()
const closeButton = ref<HTMLButtonElement | null>(null)
let previousActiveElement: HTMLElement | null = null
let previousBodyOverflow = ''

const reviewLayers = computed<LayerResult[]>(() => {
  if (!props.review?.ai_result) return []
  return [
    props.review.ai_result.layer1,
    props.review.ai_result.layer2,
    props.review.ai_result.layer3,
    props.review.ai_result.layer4,
  ].filter((layer): layer is LayerResult => Boolean(layer))
})

function riskTypeLabel(value?: string) {
  return ({ high: '高风险问题', medium: '中风险问题', low: '低风险问题', severe: '严重风险问题' } as Record<string, string>)[value || ''] || value || '合规风险'
}

function close() { emit('close') }
function formatDate(value?: string | null) { return value ? new Date(value).toLocaleString() : '-' }

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.open) close()
}

watch(() => props.open, async (open) => {
  if (open) {
    previousActiveElement = document.activeElement as HTMLElement | null
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    await nextTick()
    closeButton.value?.focus()
  } else {
    document.body.style.overflow = previousBodyOverflow
    previousActiveElement?.focus()
  }
})

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (props.open) document.body.style.overflow = previousBodyOverflow
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="history-drawer-backdrop" @click.self="close">
      <aside class="history-drawer" role="dialog" aria-modal="true" aria-label="历史审核版本">
        <div class="history-drawer-header">
          <div>
            <p class="text-xs text-gray-400">历史版本</p>
            <h3 class="font-semibold text-gray-800 dark:text-gray-100">{{ version?.version_label }}</h3>
          </div>
          <button ref="closeButton" class="btn-outline text-sm" type="button" @click="close">关闭</button>
        </div>
        <div class="history-drawer-content">
          <div v-if="loading" class="py-12 text-center text-sm text-gray-500">正在加载历史审核报告…</div>
          <div v-else-if="error" class="rounded-lg bg-red-50 text-red-700 p-3 text-sm" role="alert">{{ error }}</div>
          <template v-else>
            <p v-if="!version?.snapshot_complete" class="rounded-lg bg-yellow-50 text-yellow-700 p-3 text-sm">该历史记录未保存完整提交快照，以下只展示仍可读取的审核信息。</p>
            <section v-if="version?.submission" class="space-y-2">
              <h4>当次提交</h4>
              <p class="text-sm text-gray-500">{{ version.submission.industry }} · {{ version.submission.platforms.join('、') || '未指定平台' }}</p>
              <p class="history-drawer-text">{{ version.submission.raw_text }}</p>
            </section>
            <section>
              <h4>审查报告</h4>
              <p class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ review?.ai_result?.summary || '该历史记录未保存完整审查报告。' }}</p>
              <div v-for="layer in reviewLayers" :key="layer.layer" class="mt-3">
                <p class="text-sm font-medium">{{ layer.layer }}</p>
                <p v-for="rule in layer.matched_rules" :key="rule.rule_id" class="text-sm text-red-600 mt-1">
                  {{ riskTypeLabel(rule.match_type) }}：{{ rule.evidence_quote || rule.rule_text }}
                  <span class="text-xs text-gray-400">{{ rule.source_law }}</span>
                </p>
              </div>
            </section>
            <section>
              <h4>法务审核</h4>
              <p class="text-sm text-gray-700 dark:text-gray-300">{{ version?.legal_review_label }}</p>
              <p v-if="version?.return_reasons" class="text-sm text-red-600 mt-2">退回原因：{{ version.return_reasons }}</p>
              <p v-if="version?.legal_notes" class="text-sm text-gray-500 mt-1">备注：{{ version.legal_notes }}</p>
              <p class="text-xs text-gray-400 mt-2">提交：{{ formatDate(version?.created_at) }}；法务：{{ formatDate(version?.reviewed_at) }}</p>
            </section>
          </template>
        </div>
      </aside>
    </div>
  </Teleport>
</template>
