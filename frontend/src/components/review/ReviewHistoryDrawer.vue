<script setup lang="ts">
import type { MaterialVersion, Review } from '@/types'

defineProps<{
  open: boolean
  version: MaterialVersion | null
  review: Review | null
}>()

const emit = defineEmits<{ close: [] }>()

function close() { emit('close') }
function formatDate(value?: string | null) { return value ? new Date(value).toLocaleString() : '-' }
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
          <button class="btn-outline text-sm" type="button" @click="close">关闭</button>
        </div>
        <div class="history-drawer-content">
          <p v-if="!version?.snapshot_complete" class="rounded-lg bg-yellow-50 text-yellow-700 p-3 text-sm">该历史记录未保存完整提交快照，以下只展示仍可读取的审核信息。</p>
          <section v-if="version?.submission" class="space-y-2">
            <h4>当次提交</h4>
            <p class="text-sm text-gray-500">{{ version.submission.industry }} · {{ version.submission.platforms.join('、') || '未指定平台' }}</p>
            <p class="history-drawer-text">{{ version.submission.raw_text }}</p>
          </section>
          <section>
            <h4>审查报告</h4>
            <p class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{{ review?.ai_result?.summary || '该历史记录未保存完整审查报告。' }}</p>
            <div v-for="layer in review ? [review.ai_result.layer1, review.ai_result.layer2, review.ai_result.layer3, review.ai_result.layer4] : []" :key="layer.layer" class="mt-3">
              <p class="text-sm font-medium">{{ layer.layer }}</p>
              <p v-for="rule in layer.matched_rules" :key="rule.rule_id" class="text-sm text-red-600 mt-1">{{ rule.rule_text }} <span class="text-xs text-gray-400">{{ rule.source_law }}</span></p>
            </div>
          </section>
          <section>
            <h4>法务审核</h4>
            <p class="text-sm text-gray-700 dark:text-gray-300">{{ version?.legal_review_label }}</p>
            <p v-if="version?.return_reasons" class="text-sm text-red-600 mt-2">退回原因：{{ version.return_reasons }}</p>
            <p v-if="version?.legal_notes" class="text-sm text-gray-500 mt-1">备注：{{ version.legal_notes }}</p>
            <p class="text-xs text-gray-400 mt-2">提交：{{ formatDate(version?.created_at) }}；法务：{{ formatDate(version?.reviewed_at) }}</p>
          </section>
        </div>
      </aside>
    </div>
  </Teleport>
</template>
