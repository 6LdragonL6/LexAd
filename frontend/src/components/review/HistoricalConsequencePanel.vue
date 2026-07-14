<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  value?: unknown
}>()

interface ConsequenceItem {
  key: string
  label: string
  value: string
}

const expanded = ref(false)

const fieldLabels: Record<string, string> = {
  reputation: '舆论影响',
  business: '商业影响',
  regulatory: '监管结果',
  duration_days: '影响持续时间',
  severity_hint: '历史严重程度',
}

const fieldOrder = ['reputation', 'business', 'regulatory', 'duration_days', 'severity_hint']

const severityLabels: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  severe: '严重',
  uncertain: '不确定',
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.trim().length === 0
  if (Array.isArray(value)) return value.length === 0 || value.every(isEmpty)
  if (isRecord(value)) {
    const values = Object.values(value)
    return values.length === 0 || values.every(isEmpty)
  }
  return false
}

function fieldLabel(key: string): string {
  return fieldLabels[key] || key.replace(/[_-]+/g, ' ').trim() || '其他信息'
}

function formatValue(value: unknown, key = ''): string {
  if (isEmpty(value)) return ''

  if (key === 'duration_days' && (typeof value === 'number' || typeof value === 'string')) {
    const duration = String(value).trim()
    return duration.endsWith('天') ? duration : `${duration} 天`
  }

  if (key === 'severity_hint' && typeof value === 'string') {
    return severityLabels[value.trim().toLowerCase()] || value.trim()
  }

  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'bigint') return String(value)
  if (typeof value === 'boolean') return value ? '是' : '否'

  if (Array.isArray(value)) {
    return value
      .map(item => formatValue(item))
      .filter(Boolean)
      .join('、')
  }

  if (isRecord(value)) {
    return Object.entries(value)
      .filter(([, item]) => !isEmpty(item))
      .map(([nestedKey, item]) => `${fieldLabel(nestedKey)}：${formatValue(item, nestedKey)}`)
      .filter(item => !item.endsWith('：'))
      .join('；')
  }

  return String(value)
}

const items = computed<ConsequenceItem[]>(() => {
  if (!isRecord(props.value)) {
    const formatted = formatValue(props.value)
    return formatted ? [{ key: 'value', label: '历史影响', value: formatted }] : []
  }

  return Object.entries(props.value)
    .filter(([, value]) => !isEmpty(value))
    .sort(([left], [right]) => {
      const leftIndex = fieldOrder.indexOf(left)
      const rightIndex = fieldOrder.indexOf(right)
      if (leftIndex === -1 && rightIndex === -1) return 0
      if (leftIndex === -1) return 1
      if (rightIndex === -1) return -1
      return leftIndex - rightIndex
    })
    .map(([key, value]) => ({
      key,
      label: fieldLabel(key),
      value: formatValue(value, key),
    }))
    .filter(item => item.value)
})
</script>

<template>
  <div class="mt-3 border-t border-gray-100 dark:border-gray-700 pt-3">
    <button
      type="button"
      class="inline-flex items-center gap-1.5 text-sm font-medium text-purple-600 dark:text-purple-300 hover:text-purple-700 dark:hover:text-purple-200 transition-colors"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <svg
        class="h-4 w-4 transition-transform"
        :class="expanded ? 'rotate-180' : ''"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z" clip-rule="evenodd" />
      </svg>
      {{ expanded ? '收起历史影响' : '查看历史影响' }}
    </button>

    <div v-if="expanded" class="mt-3">
      <div v-if="items.length" class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div
          v-for="item in items"
          :key="item.key"
          class="rounded-lg bg-gray-50 dark:bg-gray-800/70 px-3 py-2.5 min-w-0"
        >
          <p class="text-xs font-medium text-gray-400">{{ item.label }}</p>
          <p class="mt-1 text-sm leading-6 text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words">{{ item.value }}</p>
        </div>
      </div>
      <p v-else class="rounded-lg bg-gray-50 dark:bg-gray-800/70 px-3 py-2.5 text-sm text-gray-400">
        暂无可展示的历史影响信息
      </p>
    </div>
  </div>
</template>
