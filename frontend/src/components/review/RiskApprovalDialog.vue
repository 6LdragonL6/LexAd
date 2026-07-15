<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps<{
  open: boolean
  issueCount: number
  highestRisk: string
  submitting?: boolean
  error?: string
}>()

const emit = defineEmits<{ cancel: []; confirm: [] }>()
const cancelButton = ref<HTMLButtonElement | null>(null)
let previousActiveElement: HTMLElement | null = null
let previousBodyOverflow = ''

function cancel() {
  if (!props.submitting) emit('cancel')
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.open) cancel()
}

watch(() => props.open, async open => {
  if (open) {
    previousActiveElement = document.activeElement as HTMLElement | null
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    await nextTick()
    cancelButton.value?.focus()
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
    <div v-if="open" class="review-dialog-backdrop" @click.self="cancel">
      <section class="review-dialog" role="alertdialog" aria-modal="true" aria-labelledby="risk-dialog-title" aria-describedby="risk-dialog-description">
        <div class="review-dialog-icon" aria-hidden="true">!</div>
        <h2 id="risk-dialog-title" class="text-lg font-semibold text-gray-900 dark:text-gray-100">确认带风险通过？</h2>
        <p id="risk-dialog-description" class="mt-2 text-sm text-gray-600 dark:text-gray-300 leading-6">
          AI 已确认 {{ issueCount }} 项风险，最高等级为“{{ highestRisk }}”。通过后物料将进入已通过状态，请确认已逐项完成人工复核。
        </p>
        <p v-if="error" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300" role="alert">{{ error }}</p>
        <div class="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <button ref="cancelButton" type="button" class="btn-outline" :disabled="submitting" @click="cancel">取消并继续复核</button>
          <button type="button" class="btn-danger" :disabled="submitting" @click="emit('confirm')">
            {{ submitting ? '提交中…' : '确认带风险通过' }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>
