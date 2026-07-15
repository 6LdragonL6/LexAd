<script setup lang="ts">
import type { ReviewStage, ReviewStageStatus } from '@/types'

defineProps<{ stages: ReviewStage[] }>()

const labels: Record<ReviewStageStatus, string> = {
  pending: '等待中',
  running: '进行中',
  completed: '已完成',
  manual_review: '需人工复核',
  failed: '执行失败',
}

function symbol(status: ReviewStageStatus) {
  if (status === 'completed') return '✓'
  if (status === 'failed') return '!'
  if (status === 'manual_review') return 'i'
  return ''
}
</script>

<template>
  <ol class="review-progress" aria-label="AI 审查进度">
    <li v-for="stage in stages" :key="stage.key" class="review-progress-item" :data-status="stage.status">
      <div class="review-progress-marker" :class="{ 'is-running': stage.status === 'running' }" aria-hidden="true">
        <span>{{ symbol(stage.status) }}</span>
      </div>
      <div class="min-w-0 flex-1">
        <div class="flex items-center justify-between gap-3">
          <span class="font-medium text-gray-800 dark:text-gray-100">{{ stage.label }}</span>
          <span class="text-xs review-progress-status">{{ labels[stage.status] }}</span>
        </div>
      </div>
    </li>
  </ol>
</template>
